"""
FAISS 向量库 CRUD —— 持久化存储与增量更新。
"""
import os
from langchain_community.vectorstores import FAISS
from config import CONFIG


class VectorStore:
    """
    FAISS 向量库管理器。

    支持:
      - 从零构建索引
      - 增量添加文档
      - 持久化到本地磁盘
      - 从磁盘加载已有索引

    用法:
        vs = VectorStore(embedding_service)
        vs.build_from_docs(docs)          # 新建索引
        vs.add_documents(new_docs)        # 增量添加
        vs.save()                         # 持久化
    """

    def __init__(self, embedding_service):
        self.embedding = embedding_service.model  # HuggingFaceEmbeddings 实例
        self._store: FAISS | None = None
        self._path = CONFIG.vector_store_path

    def build_from_docs(self, documents: list):
        """从文档列表新建 FAISS 索引"""
        self._store = FAISS.from_documents(documents, self.embedding)

    def add_documents(self, documents: list):
        """增量添加文档到已有索引"""
        if self._store is None:
            self.build_from_docs(documents)
        else:
            self._store.add_documents(documents)

    def save(self):
        """持久化索引到磁盘"""
        if self._store is not None:
            os.makedirs(self._path, exist_ok=True)
            self._store.save_local(self._path)

    def load(self) -> bool:
        """从磁盘加载索引，返回是否加载成功"""
        index_path = os.path.join(self._path, "index.faiss")
        if os.path.exists(index_path):
            self._store = FAISS.load_local(
                self._path, self.embedding,
                allow_dangerous_deserialization=True
            )
            return True
        return False

    def exists(self) -> bool:
        """检查磁盘上是否有索引文件"""
        return os.path.exists(os.path.join(self._path, "index.faiss"))

    @property
    def store(self) -> FAISS | None:
        """返回底层 FAISS 实例（供 retriever 使用）"""
        return self._store
