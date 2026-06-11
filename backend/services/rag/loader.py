"""
文档加载器 —— 支持 PDF / Word / TXT。
"""
import os
from typing import List
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


class DocumentLoader:
    """加载多种格式文档，返回 LangChain Document 列表"""

    @staticmethod
    def load(file_path: str) -> list:
        """
        根据文件扩展名选择加载器，返回 List[Document]。

        用法:
            docs = DocumentLoader.load("data/docs/景区介绍.pdf")
        """
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {ext}，仅支持 {SUPPORTED_EXTENSIONS}")

        if ext == ".pdf":
            loader = PyPDFLoader(file_path)
        elif ext == ".docx":
            loader = Docx2txtLoader(file_path)
        elif ext == ".txt":
            loader = TextLoader(file_path, encoding="utf-8")

        return loader.load()

    @staticmethod
    def load_multiple(file_paths: List[str]) -> list:
        """批量加载多个文档"""
        all_docs = []
        for fp in file_paths:
            all_docs.extend(DocumentLoader.load(fp))
        return all_docs
