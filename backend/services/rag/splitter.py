"""
文本分块器 —— 按段落+语义切分。
"""
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import CONFIG


class TextSplitter:
    """
    递归字符分块器。

    策略:
      chunk_size=500, chunk_overlap=100
      优先按段落(\\n\\n)、句子(。！？\\n)、字符顺序切分
    """

    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or CONFIG.chunk_size
        self.chunk_overlap = chunk_overlap or CONFIG.chunk_overlap
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
            length_function=len,
        )

    def split(self, documents: list) -> list:
        """分块文档列表，返回 List[Document]"""
        return self._splitter.split_documents(documents)

    def split_text(self, text: str) -> list[str]:
        """分块纯文本"""
        return self._splitter.split_text(text)
