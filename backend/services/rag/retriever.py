"""
混合检索器 —— 向量检索 + BM25 关键词检索，结果合并去重。
"""
from typing import List
from langchain_core.documents import Document
from config import CONFIG


class HybridRetriever:
    """
    混合检索：向量语义匹配 + BM25 关键词匹配。

    策略:
      1. FAISS 向量检索 → top_k 个结果
      2. BM25 关键词检索 → top_k 个结果
      3. 合并去重 → 按分数排序 → 返回 top_k

    用法:
        retriever = HybridRetriever(vector_store)
        docs = retriever.retrieve("西湖有什么历史典故？")
    """

    def __init__(self, vector_store, bm25_docs: list = None):
        self.vector_store = vector_store
        self._bm25_docs = bm25_docs or []
        self._bm25_index = None
        self.top_k = CONFIG.retrieval_top_k

        # 如果有文档，初始化 BM25
        if self._bm25_docs:
            self._build_bm25()

    def _build_bm25(self):
        """构建 BM25 关键词索引"""
        try:
            from langchain_community.retrievers import BM25Retriever
            self._bm25_index = BM25Retriever.from_documents(
                self._bm25_docs, k=self.top_k
            )
        except ImportError:
            self._bm25_index = None

    def set_documents(self, documents: List[Document]):
        """设置/更新文档库（用于 BM25 索引和后备检索）"""
        self._bm25_docs = documents
        self._build_bm25()

    def retrieve(self, query: str, top_k: int = None) -> List[Document]:
        """
        混合检索主入口。

        返回: List[Document] 去重后的检索结果
        """
        k = top_k or self.top_k
        results = []
        seen = set()

        # 1. 向量检索
        if self.vector_store and self.vector_store.store:
            vector_results = self.vector_store.store.similarity_search(query, k=k)
            for doc in vector_results:
                key = doc.page_content[:50]  # 用前50字符做去重key
                if key not in seen:
                    seen.add(key)
                    results.append(doc)

        # 2. BM25 关键词检索
        if self._bm25_index:
            try:
                bm25_results = self._bm25_index.invoke(query)
                for doc in bm25_results[:k]:
                    key = doc.page_content[:50]
                    if key not in seen:
                        seen.add(key)
                        results.append(doc)
            except Exception:
                pass

        # 3. 如果都没结果，返回空
        return results[:k]

    def get_context(self, query: str, top_k: int = None) -> str:
        """检索并拼接为 LLM 上下文文本"""
        docs = self.retrieve(query, top_k)
        if not docs:
            return ""
        return "\n---\n".join(doc.page_content for doc in docs)
