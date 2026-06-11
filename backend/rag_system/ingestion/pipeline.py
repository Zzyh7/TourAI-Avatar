"""
IngestionPipeline —— 文档解析 → 分块 → 向量化 → 存储 全流程编排。

支持两种模式:
  1. merge (默认): 增量添加，保留现有索引数据，维持 FAISS↔SQLite 对齐
  2. rebuild:      清空现有索引，从零重建（用于修复对齐问题或完全替换数据）

核心流程:
  parse → chunk → [SQLite insert → tag chunk_id → FAISS+BM25 add] → validate → persist

用法:
    from rag_system.ingestion import IngestionPipeline
    from rag_system import init_rag

    init_rag()  # 初始化 RAG 服务

    pipeline = IngestionPipeline()
    result = pipeline.ingest_structured_docx("path/to/数据集.docx")
    print(result.summary())
"""
import os
import json
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from langchain_core.documents import Document

from .parser import DocxParser, DocxParserError
from .chunkers import (
    structured_rows_to_documents,
    narrative_paragraphs_to_documents,
)


@dataclass
class IngestResult:
    """单次摄入操作的结果"""
    file_path: str
    file_name: str
    source_type: str            # "structured" | "guide"
    doc_id: int | None          # SQLite documents 表 id
    chunk_count: int
    chunk_ids: List[int] = field(default_factory=list)
    parse_info: Dict[str, Any] = field(default_factory=dict)
    faiss_aligned: bool = False
    elapsed_seconds: float = 0.0
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None

    def summary(self) -> str:
        lines = [
            f"[FILE] {self.file_name}",
            f"   类型: {self.source_type}",
            f"   分块: {self.chunk_count} 个",
            f"   对齐: {'[OK]' if self.faiss_aligned else '[WARN] 未对齐'}",
            f"   耗时: {self.elapsed_seconds:.1f}s",
        ]
        if self.error:
            lines.append(f"   [ERROR] 错误: {self.error}")
        return "\n".join(lines)


class IngestionPipeline:
    """
    文档摄入流水线。

    依赖已初始化的 RAG 服务（EmbeddingService, HybridRetriever, DocumentStore）。
    通过 get_* 懒加载函数获取全局单例。

    用法:
        pipeline = IngestionPipeline()

        # 摄入结构化表格文档
        result = pipeline.ingest_structured_docx("灵山胜境 景点结构化数据集.docx")

        # 摄入叙述性文档
        result = pipeline.ingest_narrative_docx("灵山胜境 游览指南.docx")

        # 批量摄入
        results = pipeline.ingest_batch([
            ("structured", "data.docx"),
            ("guide", "guide.docx"),
        ])
    """

    def __init__(self):
        self._embedder = None
        self._retriever = None
        self._doc_store = None

    # ---------- 懒加载 RAG 服务 ----------

    @property
    def embedder(self):
        if self._embedder is None:
            from ..api import get_embedder
            self._embedder = get_embedder()
        return self._embedder

    @property
    def retriever(self):
        if self._retriever is None:
            from ..api import get_retriever
            self._retriever = get_retriever()
        return self._retriever

    @property
    def doc_store(self):
        if self._doc_store is None:
            from ..api import get_doc_store
            self._doc_store = get_doc_store()
        return self._doc_store

    # ---------- 公开 API ----------

    def ingest_structured_docx(
        self,
        file_path: str,
        source_type: str = "structured",
    ) -> IngestResult:
        """
        摄入结构化表格 .docx 文档。

        流程:
          1. 解析 .docx → 提取所有表格行
          2. 每行 → 自然语言文本块 + metadata
          3. 写入 SQLite（获取 chunk_id）
          4. 标记 chunk_id → 写入 FAISS + BM25
          5. 校验对齐

        Args:
            file_path: .docx 文件绝对路径
            source_type: 元数据 source_type 标签

        Returns:
            IngestResult
        """
        start = time.time()
        try:
            # 1. 解析
            parser = DocxParser(file_path)
            tables = parser.extract_tables()
            parse_info = parser.get_info()

            if not tables:
                return IngestResult(
                    file_path=file_path,
                    file_name=parser.file_name,
                    source_type=source_type,
                    doc_id=None,
                    chunk_count=0,
                    parse_info=parse_info,
                    elapsed_seconds=time.time() - start,
                    error="文档中未找到表格数据",
                )

            print(f"[STATS] 解析到 {len(tables)} 个表格 (共 {sum(t['row_count'] for t in tables)} 行)")

            # 2. 转为 LangChain Documents
            documents = structured_rows_to_documents(
                tables,
                source_file=parser.file_name,
                source_type=source_type,
            )

            # 3-5. 存入 RAG 系统
            doc_id, chunk_ids, aligned = self._store_documents(
                documents=documents,
                filename=parser.file_name,
                file_type="docx",
                size_bytes=parser.file_size,
                embedding_model=self.embedder.model_name,
            )

            elapsed = time.time() - start
            print(f"[OK] 结构化文档摄入完成: {len(documents)} 个块, {elapsed:.1f}s")

            return IngestResult(
                file_path=file_path,
                file_name=parser.file_name,
                source_type=source_type,
                doc_id=doc_id,
                chunk_count=len(documents),
                chunk_ids=chunk_ids,
                parse_info=parse_info,
                faiss_aligned=aligned,
                elapsed_seconds=elapsed,
            )

        except FileNotFoundError as e:
            return IngestResult(
                file_path=file_path,
                file_name=os.path.basename(file_path),
                source_type=source_type,
                doc_id=None,
                chunk_count=0,
                elapsed_seconds=time.time() - start,
                error=f"文件不存在: {e}",
            )
        except DocxParserError as e:
            return IngestResult(
                file_path=file_path,
                file_name=os.path.basename(file_path),
                source_type=source_type,
                doc_id=None,
                chunk_count=0,
                elapsed_seconds=time.time() - start,
                error=f"解析失败: {e}",
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return IngestResult(
                file_path=file_path,
                file_name=os.path.basename(file_path),
                source_type=source_type,
                doc_id=None,
                chunk_count=0,
                elapsed_seconds=time.time() - start,
                error=f"未预期错误: {e}",
            )

    def ingest_narrative_docx(
        self,
        file_path: str,
        source_type: str = "guide",
        max_chars: int = 500,
        target_chars: int = 380,
        min_chars: int = 100,
    ) -> IngestResult:
        """
        摄入叙述性 .docx 文档。

        流程:
          1. 解析 .docx → 提取段落（保留标题层级）
          2. 按标题分组 → 语义段落切块 (300~500字)
          3. 写入 SQLite（获取 chunk_id）
          4. 标记 chunk_id → 写入 FAISS + BM25
          5. 校验对齐

        Args:
            file_path: .docx 文件绝对路径
            source_type: 元数据 source_type 标签
            max_chars:   单块最大字符数
            target_chars: 单块目标字符数
            min_chars:   最小块字符数

        Returns:
            IngestResult
        """
        start = time.time()
        try:
            # 1. 解析
            parser = DocxParser(file_path)
            paragraphs = parser.extract_paragraphs()
            parse_info = parser.get_info()

            if not paragraphs:
                return IngestResult(
                    file_path=file_path,
                    file_name=parser.file_name,
                    source_type=source_type,
                    doc_id=None,
                    chunk_count=0,
                    parse_info=parse_info,
                    elapsed_seconds=time.time() - start,
                    error="文档中未找到文本段落",
                )

            print(f"[TEXT] 解析到 {len(paragraphs)} 个非空段落")

            # 2. 转为 LangChain Documents
            documents = narrative_paragraphs_to_documents(
                paragraphs,
                source_file=parser.file_name,
                source_type=source_type,
                max_chars=max_chars,
                target_chars=target_chars,
                min_chars=min_chars,
            )

            # 3-5. 存入 RAG 系统
            doc_id, chunk_ids, aligned = self._store_documents(
                documents=documents,
                filename=parser.file_name,
                file_type="docx",
                size_bytes=parser.file_size,
                embedding_model=self.embedder.model_name,
            )

            elapsed = time.time() - start
            print(f"[OK] 叙述性文档摄入完成: {len(documents)} 个块, {elapsed:.1f}s")

            return IngestResult(
                file_path=file_path,
                file_name=parser.file_name,
                source_type=source_type,
                doc_id=doc_id,
                chunk_count=len(documents),
                chunk_ids=chunk_ids,
                parse_info=parse_info,
                faiss_aligned=aligned,
                elapsed_seconds=elapsed,
            )

        except FileNotFoundError as e:
            return IngestResult(
                file_path=file_path,
                file_name=os.path.basename(file_path),
                source_type=source_type,
                doc_id=None,
                chunk_count=0,
                elapsed_seconds=time.time() - start,
                error=f"文件不存在: {e}",
            )
        except DocxParserError as e:
            return IngestResult(
                file_path=file_path,
                file_name=os.path.basename(file_path),
                source_type=source_type,
                doc_id=None,
                chunk_count=0,
                elapsed_seconds=time.time() - start,
                error=f"解析失败: {e}",
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return IngestResult(
                file_path=file_path,
                file_name=os.path.basename(file_path),
                source_type=source_type,
                doc_id=None,
                chunk_count=0,
                elapsed_seconds=time.time() - start,
                error=f"未预期错误: {e}",
            )

    def ingest_batch(
        self,
        tasks: List[tuple],  # [(source_type, file_path), ...]
    ) -> List[IngestResult]:
        """
        批量摄入多个文档。

        Args:
            tasks: [(source_type, file_path), ...]
                   source_type: "structured" | "guide"

        Returns:
            List[IngestResult]
        """
        results = []
        for source_type, file_path in tasks:
            if source_type == "structured":
                result = self.ingest_structured_docx(file_path)
            elif source_type == "guide":
                result = self.ingest_narrative_docx(file_path)
            else:
                result = IngestResult(
                    file_path=file_path,
                    file_name=os.path.basename(file_path),
                    source_type=source_type,
                    doc_id=None,
                    chunk_count=0,
                    error=f"未知的 source_type: {source_type}",
                )
            results.append(result)
        return results

    # ---------- 内部方法 ----------

    def _store_documents(
        self,
        documents: List[Document],
        filename: str,
        file_type: str,
        size_bytes: int,
        embedding_model: str,
    ) -> tuple:
        """
        将 LangChain Document 列表存入 RAG 系统。

        关键顺序（确保 FAISS ↔ SQLite 对齐）:
          1. SQLite 先写入 → 获取 chunk_ids
          2. 将 chunk_id + embedding_model 标记到每个 Document.metadata
          3. FAISS + BM25 后写入（Document 已携带 SQLite ID）

        Returns:
            (doc_id, chunk_ids, faiss_aligned)
        """
        if not documents:
            return None, [], True

        # === 1. SQLite 先写入 ===
        doc_id, chunk_ids = self.doc_store.add_document(
            filename=filename,
            file_type=file_type,
            chunks=documents,
            size_bytes=size_bytes,
            embedding_model=embedding_model,
        )

        # === 2. 将 chunk_id 和 embedding_model 标记到 metadata ===
        for chunk, cid in zip(documents, chunk_ids):
            chunk.metadata["chunk_id"] = cid
            chunk.metadata["embedding_model"] = embedding_model

        # === 3. FAISS + BM25 后写入 ===
        self.retriever.add_documents(documents)

        # === 4. 校验 FAISS ↔ SQLite 对齐 ===
        alignment = self.doc_store.validate_faiss_alignment(
            self.retriever.stats["faiss_vectors"]
        )
        if not alignment["aligned"]:
            print(f"[WARN] FAISS/SQLite 对齐警告: {alignment['detail']}")

        return doc_id, chunk_ids, alignment["aligned"]

    def rebuild_from_existing(self) -> bool:
        """
        从 SQLite 中所有 chunks 重建 FAISS + BM25 索引。

        用于修复对齐问题，或更换嵌入模型后重建。
        注意：此操作会清空当前 FAISS/BM25 索引并从 SQLite 完全重建。

        Returns:
            True 如果重建成功
        """
        from langchain_core.documents import Document as LCDocument
        from langchain_community.vectorstores import FAISS
        from langchain_community.vectorstores.faiss import DistanceStrategy

        chunks = self.doc_store.get_all_chunks_full()
        if not chunks:
            print("[INFO] SQLite 中无块数据，跳过重建")
            return False

        print(f"[REBUILD] 从 SQLite 重建索引 ({len(chunks)} 个块)...")

        # 构建 LangChain Documents
        documents = []
        bm25_corpus = []
        bm25_metadata = []

        for ch in chunks:
            # 解析 metadata JSON
            meta = {}
            if ch.get("metadata"):
                try:
                    meta = json.loads(ch["metadata"]) if isinstance(ch["metadata"], str) else ch["metadata"]
                except json.JSONDecodeError:
                    meta = {}

            # 确保 chunk_id 存在
            meta["chunk_id"] = ch["id"]

            doc = LCDocument(page_content=ch["content"], metadata=meta)
            documents.append(doc)
            bm25_corpus.append(ch["content"])
            bm25_metadata.append({
                "source": ch.get("source_file", "未知"),
                "chunk_index": ch.get("chunk_index", -1),
                "chunk_id": ch["id"],
                "embedding_model": ch.get("embedding_model", ""),
            })

        # 重建 FAISS
        import jieba
        from rank_bm25 import BM25Okapi

        self.retriever._faiss_store = FAISS.from_documents(
            documents,
            self.embedder.model,
            distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT,
        )

        # 重建 BM25
        self.retriever._bm25_corpus = bm25_corpus
        self.retriever._bm25_metadata = bm25_metadata
        tokenized = [list(jieba.cut(text)) for text in bm25_corpus]
        self.retriever._bm25 = BM25Okapi(tokenized)

        # 持久化
        self.retriever._save_all()

        # 校验
        alignment = self.doc_store.validate_faiss_alignment(
            self.retriever.stats["faiss_vectors"]
        )
        print(f"[OK] 重建完成: {alignment['detail']}")
        return alignment["aligned"]

    def get_stats(self) -> dict:
        """获取当前 RAG 系统统计信息"""
        stats = self.retriever.stats
        return {
            **stats,
            "documents_count": self.doc_store.get_document_count(),
            "chunks_count": self.doc_store.get_chunk_count(),
            "aligned": self.doc_store.validate_faiss_alignment(
                stats["faiss_vectors"]
            )["aligned"],
        }
