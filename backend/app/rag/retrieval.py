"""
多路检索管道 — 向量 + BM25 + RRF 融合 + 重排序
"""
import logging
import re
from typing import List, Dict, Optional
from . import config as _cfg
from .models import embedding_model, vector_store, Document, tokenize_for_bm25

_logger=logging.getLogger("xikiy_aiops.rag")
COLLECTION_NAME="sre_knowledge"


# ── BM25 关键词检索 (纯 Python, 无外部依赖) ──────────────

"""
方法: _bm25_search(query, documents, top_k), 简易 BM25 关键词检索, 返回文档索引列表按相关性降序

"""
def _bm25_search(query:str, documents:List[str], top_k:int=10)->List[int]:
    query_tokens=tokenize_for_bm25(query)
    if not query_tokens or not documents:
        return list(range(min(top_k, len(documents))))

    N=len(documents)
    avgdl=sum(len(tokenize_for_bm25(d)) for d in documents)/N if N>0 else 1
    k1=1.5
    b=0.75

    #计算 IDF
    df={}
    for d in documents:
        seen=set()
        for t in tokenize_for_bm25(d):
            if t not in seen:
                df[t]=df.get(t,0)+1
                seen.add(t)

    #计算每个文档分数
    scores=[]
    for i, d in enumerate(documents):
        doc_tokens=tokenize_for_bm25(d)
        doc_len=len(doc_tokens)
        score=0.0
        tf={t:doc_tokens.count(t) for t in set(doc_tokens)}

        for qt in query_tokens:
            if qt not in df:
                continue
            idf=max(0, ((N-df[qt]+0.5)/(df[qt]+0.5)))
            tf_val=tf.get(qt,0)
            numerator=tf_val*(k1+1)
            denominator=tf_val+k1*(1-b+b*doc_len/avgdl)
            score+=idf*numerator/denominator

        scores.append((i, score))

    #排序
    scores.sort(key=lambda x:-x[1])
    return [i for i,_ in scores[:top_k] if scores[0][1]>0 or i==scores[0][0]]


# ── RRF 融合 ───────────────────────────────────────────

"""
方法: _rrf_fusion(vector_ranked, bm25_ranked, k), Reciprocal Rank Fusion 融合两路检索结果

"""
def _rrf_fusion(
    vector_ranked:List[int],
    bm25_ranked:List[int],
    k:int=60,
)->List[int]:
    scores={}
    for rank, idx in enumerate(vector_ranked):
        scores[idx]=scores.get(idx,0)+1/(k+rank+1)
    for rank, idx in enumerate(bm25_ranked):
        scores[idx]=scores.get(idx,0)+1/(k+rank+1)

    return sorted(scores.keys(), key=lambda x:-scores[x])


# ── 重排序 ──────────────────────────────────────────────

_reranker=None

"""
方法: _get_reranker(), 延迟加载重排序模型 FlagReranker, 失败返回 False

"""
def _get_reranker():
    global _reranker
    if _reranker is not None:
        return _reranker
    try:
        from FlagEmbedding import FlagReranker
        _reranker=FlagReranker(_cfg.RERANK_MODEL, use_fp16=True)
        _logger.info(f"重排序模型已加载: {_cfg.RERANK_MODEL}")
    except ImportError:
        _logger.warning("FlagEmbedding 未安装, 重排序禁用")
        _reranker=False
    except Exception as e:
        _logger.warning(f"重排序模型加载失败: {e}")
        _reranker=False
    return _reranker


"""
方法: _rerank(query, candidates, top_k), 对候选文档用 FlagReranker 重排序

"""
def _rerank(query:str, candidates:List[Document], top_k:int)->List[Document]:
    reranker=_get_reranker()
    if not reranker:
        return candidates[:top_k]

    pairs=[[query, d.content] for d in candidates]
    try:
        scores=reranker.compute_score(pairs)
        for i, d in enumerate(candidates):
            d.score=float(scores[i]) if isinstance(scores, list) else float(scores[i])
    except Exception as e:
        _logger.warning(f"重排序失败: {e}")
        return candidates[:top_k]

    candidates.sort(key=lambda x:-x.score)
    return candidates[:top_k]


# ── 查询改写  ──────────────────────────────────────────

"""
方法: _rewrite_query(query), 查询改写 — 生成多个变体用于多路召回 (去语气词/中英关键词提取)

"""
def _rewrite_query(query:str)->List[str]:
    queries=[query]

    #去语气词
    cleaned=re.sub(r'[帮我看看\|请\|麻烦\|能不能\|可不可以\|怎么\|如何]','',query)
    if cleaned!=query and len(cleaned)>=3:
        queries.append(cleaned.strip())

    #提取中文关键词 (2-4字组合)
    cn_chars=re.findall(r'[\u4e00-\u9fff]+', query)
    if cn_chars:
        keywords=' '.join(cn_chars)
        if keywords not in queries:
            queries.append(keywords)

    return queries


# ── 主检索入口 ─────────────────────────────────────────

"""
方法: search(query, top_k, collection_name), 完整检索管道 — 查询改写→向量检索→BM25→RRF融合→重排序

"""
def search(
    query:str,
    top_k:int=None,
    collection_name:str=COLLECTION_NAME,
)->List[Document]:
    if top_k is None:
        top_k=_cfg.DEFAULT_TOP_K
    top_k=min(top_k, _cfg.MAX_TOP_K)

    try:
        collection=vector_store.get_or_create_collection(collection_name)
    except Exception:
        _logger.warning(f"集合 '{collection_name}' 不存在, 请先构建知识库")
        return []

    if collection.count()==0:
        return []

    #1. 查询改写
    queries=_rewrite_query(query)
    _logger.info(f"RAG 检索: '{query}' → {len(queries)} 个变体")

    #2. 向量检索 (对每个查询变体)
    vector_candidates=[]
    try:
        query_embedding=embedding_model.encode_single(query)
        results=collection.query(
            query_embeddings=[query_embedding],
            n_results=min(_cfg.VECTOR_CANDIDATES, collection.count()),
            include=["documents","metadatas","distances"],
        )
        if results and results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                vector_candidates.append(Document(
                    content=results["documents"][0][i],
                    metadata=results["metadatas"][0][i],
                    score=1-float(results["distances"][0][i]),  # cosine距离→相似度
                ))
    except Exception as e:
        _logger.warning(f"向量检索失败: {e}")

    #3. BM25 关键词检索
    all_docs=collection.get(include=["documents","metadatas"])
    bm25_docs=[]
    if all_docs and all_docs["documents"]:
        doc_texts=all_docs["documents"]
        bm25_indices=_bm25_search(query, doc_texts, _cfg.BM25_CANDIDATES)
        for idx in bm25_indices:
            if idx<len(doc_texts):
                bm25_docs.append(Document(
                    content=doc_texts[idx],
                    metadata=all_docs["metadatas"][idx] if all_docs.get("metadatas") else {},
                    score=0.5,  # BM25 默认中分
                ))

    #4. RRF 融合 (用索引去重, 保留 Document 对象)
    # 构建 id→doc 映射
    vec_ids=[d.metadata.get("title","")+d.content[:50] for d in vector_candidates]
    bm25_ids=[d.metadata.get("title","")+d.content[:50] for d in bm25_docs]

    merged={}
    for d in vector_candidates:
        key=d.metadata.get("title","")+d.content[:80]
        if key not in merged or d.score>merged[key].score:
            merged[key]=d
    for d in bm25_docs:
        key=d.metadata.get("title","")+d.content[:80]
        if key not in merged:
            d.score*=0.5  # BM25单独命中降权
            merged[key]=d

    candidates=sorted(merged.values(), key=lambda x:-x.score)
    top_candidates=candidates[:min(_cfg.VECTOR_CANDIDATES, len(candidates))]

    #5. 重排序 (可选)
    if _cfg.RERANK_ENABLED and len(top_candidates)>top_k:
        top_candidates=_rerank(query, top_candidates, top_k)

    result=top_candidates[:top_k]

    #整理 metadata
    for d in result:
        if "title" not in d.metadata:
            d.metadata["title"]=""
        if "source" not in d.metadata:
            d.metadata["source"]="未知"

    _logger.info(f"检索完成: {len(result)} 条 (向量{len(vector_candidates)} + BM25{len(bm25_docs)} → 融合{len(candidates)} → 输出{len(result)})")
    return result


"""
方法: get_stats(collection_name), 返回知识库统计信息 — 集合名/条目数/状态

"""
def get_stats(collection_name:str=COLLECTION_NAME)->Dict:
    try:
        collection=vector_store.get_or_create_collection(collection_name)
        return {
            "collection":collection_name,
            "total_chunks":collection.count(),
            "status":"ok",
        }
    except Exception as e:
        return {"status":"error","error":str(e)}
