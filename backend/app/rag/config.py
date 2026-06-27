"""
RAG 模块 — 运维知识库配置

嵌入模型、分块参数、检索参数集中管理
"""
import os
from pathlib import Path

# 数据路径
_RAG_DIR=Path(__file__).resolve().parent
_PROJECT_DATA=os.path.join(_RAG_DIR, "..", "..", "data")
RAG_DB_DIR=os.environ.get("RAG_DB_DIR", os.path.join(_PROJECT_DATA, "rag_db"))

# 嵌入模型 (中英双语, 512维, 轻量离线)
EMBEDDING_MODEL=os.environ.get("RAG_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
EMBEDDING_DEVICE=os.environ.get("RAG_EMBEDDING_DEVICE", "cpu")  # cpu / cuda

# 分块参数
CHUNK_SIZE=int(os.environ.get("RAG_CHUNK_SIZE", "500"))      # 每块最大字符数
CHUNK_OVERLAP=int(os.environ.get("RAG_CHUNK_OVERLAP", "80")) # 重叠字符数

# 检索参数
DEFAULT_TOP_K=int(os.environ.get("RAG_DEFAULT_TOP_K", "5"))  # 默认返回条数
MAX_TOP_K=int(os.environ.get("RAG_MAX_TOP_K", "10"))         # 最大返回条数

# 多路召回
VECTOR_CANDIDATES=int(os.environ.get("RAG_VECTOR_CANDIDATES", "20"))  # 向量召回候选数
BM25_CANDIDATES=int(os.environ.get("RAG_BM25_CANDIDATES", "10"))      # BM25 召回候选数

# 重排序模型
RERANK_MODEL=os.environ.get("RAG_RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
RERANK_ENABLED=os.environ.get("RAG_RERANK_ENABLED", "0") == "1"  # 默认关闭(需要额外GPU/内存)
