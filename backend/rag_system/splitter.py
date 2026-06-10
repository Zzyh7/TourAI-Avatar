"""
文本分块器 —— 递归字符分割，适配中文景区文档。
"""
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from .config import rag_config


class TextSplitter:
    """
    中文文本递归分块器。

    策略:
      - chunk_size=500, chunk_overlap=50
      - 优先按段落(\\n\\n)、换行(\\n)、标点(。！？；，)逐级切分
      - 保证句子完整性，避免截断到词语中间
    """

    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or rag_config.chunk_size
        self.chunk_overlap = chunk_overlap or rag_config.chunk_overlap

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            # 分隔符优先级：段落 → 换行 → 句号 → 感叹号 → 问号 → 分号 → 逗号 → 空格 → 字符
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
            length_function=len,
        )

    def split_documents(self, documents: list[Document]) -> list[Document]:
        """
        分割 LangChain Document 列表。
        每个分块会继承原始文档的 metadata（如 source 文件名）。
        """
        if not documents:
            return []
        return self._splitter.split_documents(documents)

    def split_text(self, text: str) -> list[str]:
        """分割纯文本字符串"""
        if not text:
            return []
        return self._splitter.split_text(text)
