"""
RAG 运维知识库模块

文件结构:
    config.py    — 路径、模型、分块、检索参数
    models.py    — 嵌入模型 + 向量存储 (双后端自适应) + 统一分词
    index.py     — 文件 MD5 索引 (增量更新追踪)
    chunker.py   — Markdown 分块器
    ingestion.py — 知识库构建 (全量/增量)
    retrieval.py — 多路检索管道 (向量+BM25+RRF+重排序)
    inject.py    — 对话自动注入

用法:
    from app.rag import search, build_knowledge_base, get_stats
    results = search("麒麟系统 OOM 怎么排查")
    build_knowledge_base(force=True)
"""
from .retrieval import search, get_stats
from .ingestion import build_knowledge_base

__all__=["search","get_stats","build_knowledge_base"]
