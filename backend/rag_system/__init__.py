"""
RAG 知识库系统 —— 景区导览数字人的智能检索模块。

核心组件:
  - config.py              : 全局配置（路径、模型、检索参数）
  - embedding.py           : BGE-small-zh 向量化服务
  - splitter.py            : 中文文本递归分块器
  - loader.py              : 多格式文档加载器 (PDF/Word/TXT/MD)
  - document_store.py      : SQLite 文档块元数据存储
  - hybrid_retriever.py    : FAISS + BM25 + RRF 混合检索器
  - api.py                 : FastAPI 路由（上传/查询/FAQ）

快速开始:
    from rag_system import rag_router, init_rag, get_retriever

    # 在现有 FastAPI app 中挂载:
    app.include_router(rag_router, prefix="/api/rag")

    # 或在 main.py 的 lifespan 中预初始化:
    init_rag()

架构流程图:
    文档上传
      │
      ├─ PDF/Word/TXT/MD → 文本提取
      ├─ RecursiveCharacterTextSplitter (500/50)
      ├─ BGE-small-zh → 向量化
      ├─ FAISS 索引 (增量添加 + 磁盘持久化)
      ├─ BM25 索引 (jieba 分词 + 全量重建)
      └─ SQLite 元数据记录

    知识问答
      │
      ├─ FAQ 精确匹配 (阈值 0.85)
      ├─ FAISS 向量检索 (top_k=10)
      ├─ BM25 关键词检索 (top_k=10)
      ├─ RRF 排名融合 (k=60)
      ├─ 阈值检查 (< 0.6 → "不知道")
      └─ LLM 生成答案 (DeepSeek)
"""
from .config import rag_config, RAGConfig
from .embedding import EmbeddingService
from .splitter import TextSplitter
from .loader import DocumentLoader
from .document_store import DocumentStore
from .hybrid_retriever import HybridRetriever
from .api import (
    router as rag_router,
    get_retriever,
    get_embedder,
    get_doc_store,
    get_splitter,
)


def init_rag():
    """
    预初始化所有 RAG 服务（可在 FastAPI lifespan 中调用）。

    在模块首次导入时，服务是懒加载的。调用此函数可以提前加载模型，
    避免第一个请求时的冷启动延迟。
    """
    print("[RAG] Initializing knowledge base...")
    get_embedder()
    get_retriever()
    get_doc_store()
    get_splitter()
    print("[RAG] Knowledge base ready")


__all__ = [
    "rag_config",
    "RAGConfig",
    "EmbeddingService",
    "TextSplitter",
    "DocumentLoader",
    "DocumentStore",
    "HybridRetriever",
    "rag_router",
    "init_rag",
    "get_retriever",
    "get_embedder",
    "get_doc_store",
    "get_splitter",
]
