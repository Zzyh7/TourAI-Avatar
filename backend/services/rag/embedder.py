"""
向量化服务 —— 使用 BGE-small-zh 将文本转为嵌入向量。
"""
from langchain_huggingface import HuggingFaceEmbeddings
from config import CONFIG


class EmbeddingService:
    """
    BGE-small-zh 中文嵌入模型。

    用法:
        embedder = EmbeddingService()
        vectors = embedder.embed(["文本1", "文本2"])
    """

    def __init__(self, model_name: str = None):
        self.model_name = model_name or CONFIG.embedding_model
        self._model = HuggingFaceEmbeddings(
            model_name=self.model_name,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量向量化文本"""
        return self._model.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        """向量化查询文本"""
        return self._model.embed_query(text)

    @property
    def model(self):
        """返回底层 HuggingFaceEmbeddings 实例（用于 FAISS 初始化）"""
        return self._model
