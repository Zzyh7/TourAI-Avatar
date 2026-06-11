"""
文档摄入模块 —— 解析、分块、向量化、存储的全流程自动化。

支持:
  - 结构化表格 .docx → 自然语言文本块 + 完整字段 metadata
  - 叙述性文档 .docx  → 按标题语义切块 (300~500字)
  - 增量合并模式（保留现有数据，维持 FAISS↔SQLite 对齐）
  - 全量重建模式（修复对齐问题或更换嵌入模型）

典型用法:
    from rag_system import init_rag
    from rag_system.ingestion import IngestionPipeline

    init_rag()  # 初始化 RAG 服务

    pipeline = IngestionPipeline()
    pipeline.ingest_structured_docx("灵山胜境 景点结构化数据集.docx")
    pipeline.ingest_narrative_docx("灵山胜境 游览指南.docx")

    print(pipeline.get_stats())
"""
from .parser import DocxParser, DocxParserError
from .chunkers import structured_rows_to_documents, narrative_paragraphs_to_documents
from .pipeline import IngestionPipeline, IngestResult

__all__ = [
    "DocxParser",
    "DocxParserError",
    "structured_rows_to_documents",
    "narrative_paragraphs_to_documents",
    "IngestionPipeline",
    "IngestResult",
]
