"""
文档加载器 —— 支持 PDF / Word / TXT / Markdown 格式解析。
"""
import os
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    UnstructuredMarkdownLoader,
)

# 支持的文档格式
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}

# MIME 类型映射
EXT_TO_TYPE = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".txt": "txt",
    ".md": "md",
}


class DocumentLoader:
    """
    多格式文档加载器。

    支持格式:
      - .pdf   → PyPDFLoader (逐页提取文本)
      - .docx  → Docx2txtLoader (提取 Word 文本)
      - .txt   → TextLoader (UTF-8 纯文本)
      - .md    → UnstructuredMarkdownLoader (Markdown 文本)

    用法:
        docs = DocumentLoader.load("data/docs/景区介绍.pdf")
        for doc in docs:
            print(doc.page_content)
    """

    @staticmethod
    def load(file_path: str) -> List[Document]:
        """
        根据文件扩展名选择合适的加载器。

        Args:
            file_path: 文档的绝对或相对路径

        Returns:
            List[Document]: LangChain Document 列表，每个 Document 代表一页或一个段落

        Raises:
            ValueError: 不支持的文件格式
            FileNotFoundError: 文件不存在
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"不支持的文件格式: {ext}，仅支持: {', '.join(SUPPORTED_EXTENSIONS)}"
            )

        # 根据扩展名选择加载器
        docs: List[Document]
        if ext == ".pdf":
            docs = PyPDFLoader(file_path).load()
        elif ext == ".docx":
            docs = Docx2txtLoader(file_path).load()
        elif ext == ".txt":
            docs = TextLoader(file_path, encoding="utf-8").load()
        elif ext == ".md":
            # UnstructuredMarkdownLoader 需要 unstructured 库，
            # 如果不可用则回退到 TextLoader
            try:
                docs = UnstructuredMarkdownLoader(file_path).load()
            except ImportError:
                docs = TextLoader(file_path, encoding="utf-8").load()

        # 确保每个 doc 的 metadata 包含 source 文件名
        filename = os.path.basename(file_path)
        for doc in docs:
            if "source" not in doc.metadata:
                doc.metadata["source"] = filename

        return docs

    @staticmethod
    def load_multiple(file_paths: List[str]) -> List[Document]:
        """批量加载多个文档，合并返回"""
        all_docs = []
        for fp in file_paths:
            try:
                all_docs.extend(DocumentLoader.load(fp))
            except Exception as e:
                print(f"[WARN] 加载文件失败: {fp}, 错误: {e}")
        return all_docs
