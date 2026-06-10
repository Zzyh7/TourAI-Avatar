"""
向量化服务 —— 使用 BAAI/bge-small-zh-v1.5 将文本转为归一化嵌入向量。

BGE-small-zh-v1.5 特点:
  - 专为中文优化的小型嵌入模型（约 24MB）
  - 输出 512 维归一化向量
  - 归一化后余弦相似度 = 内积，可直接用于 FAISS IndexFlatIP
"""
from langchain_huggingface import HuggingFaceEmbeddings
from .config import rag_config


class EmbeddingService:
    """
    BGE-small-zh 中文嵌入模型封装。

    用法:
        embedder = EmbeddingService()
        vectors = embedder.embed_documents(["文本1", "文本2"])  # 批量
        vec = embedder.embed_query("单个查询")                   # 单条
    """

    def __init__(self, model_name: str = None, device: str = None):
        self.model_name = model_name or rag_config.embedding_model
        self.device = device or rag_config.embedding_device

        # normalize_embeddings=True 确保向量 L2 归一化，
        # 这样 FAISS 可以使用内积 (IndexFlatIP) 作为余弦相似度
        self._model = HuggingFaceEmbeddings(
            model_name=self.model_name,
            model_kwargs={"device": self.device},
            encode_kwargs={"normalize_embeddings": True},
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量文本向量化，返回 512 维向量列表"""
        if not texts:
            return []
        return self._model.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        """单条查询文本向量化"""
        return self._model.embed_query(text)

    @property
    def model(self) -> HuggingFaceEmbeddings:
        """返回底层 HuggingFaceEmbeddings 实例（供 FAISS 初始化）"""
        return self._model
