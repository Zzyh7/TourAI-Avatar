"""
文档存储 —— SQLite 管理文档块元数据与原始文本。

存储两级数据:
  1. documents 表: 上传的原始文件记录
  2. chunks 表:    每个分块的文本内容 + 元数据 + 嵌入模型

ID 对齐策略:
  FAISS 索引 ID (0-based) 与 chunks.id (1-based AUTOINCREMENT) 通过写入顺序保证一一对应:
    chunks.id = FAISS_index + 1
  前提: 两者从空开始同步增长，删除文档时需同步重建索引。

用途:
  - 追踪每个块的来源文件（用于回答时给出引用）
  - 获取所有块文本（用于重建 BM25 语料库）
  - 删除文档时级联删除所有关联块
  - 通过 chunk_id 反查 FAISS 向量
"""
import json
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Tuple
from .config import rag_config


class DocumentStore:
    """
    SQLite 文档块元数据存储。

    表结构:
      documents:
        - id           INTEGER PRIMARY KEY AUTOINCREMENT
        - filename     TEXT    (原始文件名)
        - file_type    TEXT    (pdf/docx/txt/md)
        - chunk_count  INTEGER (该文档产生的块数)
        - size_bytes   INTEGER (原始文件大小)
        - uploaded_at  TIMESTAMP

      chunks:
        - id              INTEGER PRIMARY KEY AUTOINCREMENT
        - document_id     INTEGER → documents(id) ON DELETE CASCADE
        - chunk_index     INTEGER (块在文档内的序号，从0开始)
        - content         TEXT    (块的原始文本)
        - source_file     TEXT    (来源文件名)
        - metadata        TEXT    (JSON字符串，存储LangChain Document.metadata)
        - embedding_model TEXT    (向量化所用模型，如 BAAI/bge-small-zh-v1.5)
        - created_at      TIMESTAMP
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or rag_config.db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接（启用 WAL 模式提升并发性能）"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """初始化表结构（不存在则创建；对已有表执行迁移添加新列）"""
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS documents (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename    TEXT    NOT NULL,
                    file_type   TEXT    NOT NULL,
                    chunk_count INTEGER DEFAULT 0,
                    size_bytes  INTEGER DEFAULT 0,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS chunks (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id     INTEGER NOT NULL,
                    chunk_index     INTEGER NOT NULL,
                    content         TEXT    NOT NULL,
                    source_file     TEXT    NOT NULL,
                    metadata        TEXT    DEFAULT '{}',
                    embedding_model TEXT    DEFAULT 'BAAI/bge-small-zh-v1.5',
                    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                );

                -- 索引加速查询
                CREATE INDEX IF NOT EXISTS idx_chunks_doc_id
                    ON chunks(document_id);
                CREATE INDEX IF NOT EXISTS idx_chunks_source
                    ON chunks(source_file);
            """)

            # 兼容旧表迁移：如果旧 chunks 表缺少新列则追加
            existing_cols = {
                row[1] for row in
                conn.execute("PRAGMA table_info(chunks)").fetchall()
            }
            if "metadata" not in existing_cols:
                conn.execute(
                    "ALTER TABLE chunks ADD COLUMN metadata TEXT DEFAULT '{}'"
                )
            if "embedding_model" not in existing_cols:
                conn.execute(
                    "ALTER TABLE chunks ADD COLUMN embedding_model TEXT DEFAULT 'BAAI/bge-small-zh-v1.5'"
                )

            conn.commit()

    # ==================== 文档 CRUD ====================

    def add_document(
        self,
        filename: str,
        file_type: str,
        chunks: list,       # LangChain Document 对象列表
        size_bytes: int = 0,
        embedding_model: str = None,
    ) -> Tuple[int, List[int]]:
        """
        添加文档及其所有分块。

        Args:
            filename:        原始文件名
            file_type:       文件类型 (pdf/docx/txt/md)
            chunks:          LangChain Document 列表（已分块）
            size_bytes:      原始文件大小
            embedding_model: 向量化所用模型名（默认从 config 读取）

        Returns:
            (doc_id, chunk_ids): 新创建的文档 ID 和所有块 ID 列表
        """
        if embedding_model is None:
            embedding_model = rag_config.embedding_model

        with self._get_conn() as conn:
            # 插入文档记录
            cursor = conn.execute(
                """INSERT INTO documents (filename, file_type, chunk_count, size_bytes)
                   VALUES (?, ?, ?, ?)""",
                (filename, file_type, len(chunks), size_bytes),
            )
            doc_id = cursor.lastrowid

            # 逐条插入块记录（逐条执行以确保正确获取 lastrowid）
            chunk_ids = []
            for i, chunk in enumerate(chunks):
                content = (
                    chunk.page_content
                    if hasattr(chunk, "page_content")
                    else str(chunk)
                )
                source = (
                    chunk.metadata.get("source", filename)
                    if hasattr(chunk, "metadata")
                    else filename
                )
                # 将 LangChain Document 的 metadata 字典序列化为 JSON
                metadata_json = (
                    json.dumps(chunk.metadata, ensure_ascii=False)
                    if hasattr(chunk, "metadata")
                    else "{}"
                )
                cursor = conn.execute(
                    """INSERT INTO chunks
                       (document_id, chunk_index, content, source_file, metadata, embedding_model)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (doc_id, i, content, source, metadata_json, embedding_model),
                )
                chunk_ids.append(cursor.lastrowid)

            conn.commit()
            return doc_id, chunk_ids

    def get_document(self, doc_id: int) -> dict | None:
        """获取单个文档记录"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE id = ?", (doc_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_all_documents(self) -> List[Dict]:
        """获取所有文档（按上传时间倒序）"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM documents ORDER BY uploaded_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_document(self, doc_id: int) -> bool:
        """
        删除文档及其所有块（级联删除）。

        Returns:
            True 如果删除成功，False 如果文档不存在
        """
        with self._get_conn() as conn:
            # 先查是否存在
            doc = conn.execute(
                "SELECT id, filename FROM documents WHERE id = ?", (doc_id,)
            ).fetchone()
            if not doc:
                return False

            # 级联删除块（如果外键未启用则手动删除）
            conn.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
            conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.commit()
            return True

    # ==================== 块查询 ====================

    def get_chunks_by_document(self, doc_id: int) -> List[Dict]:
        """获取某个文档的所有块（按块索引排序）"""
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM chunks
                   WHERE document_id = ?
                   ORDER BY chunk_index""",
                (doc_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_all_chunks(self) -> List[Dict]:
        """获取所有块（用于重建 BM25 语料）"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT id, document_id, chunk_index, content, source_file FROM chunks ORDER BY id"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_all_chunks_full(self) -> List[Dict]:
        """获取所有块的全部字段（含 metadata JSON、embedding_model，用于完整重建索引）"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM chunks ORDER BY id"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_chunk_count(self) -> int:
        """获取块总数"""
        with self._get_conn() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM chunks").fetchone()
            return row["cnt"]

    def get_document_count(self) -> int:
        """获取文档总数"""
        with self._get_conn() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM documents").fetchone()
            return row["cnt"]

    def validate_faiss_alignment(self, faiss_ntotal: int) -> dict:
        """
        校验 FAISS 向量数与 SQLite chunks 行数是否一致。

        对齐前提: FAISS (0-based) 与 chunks.id (1-based AUTOINCREMENT)
        从空开始同步增长，即 chunks.id = FAISS_index + 1。

        Args:
            faiss_ntotal: FAISS 索引中的向量总数

        Returns:
            {"aligned": bool, "chunks_count": int, "faiss_vectors": int, "detail": str}
        """
        chunks_count = self.get_chunk_count()
        aligned = chunks_count == faiss_ntotal
        if aligned:
            detail = "FAISS 与 SQLite chunks 已对齐"
        else:
            detail = (
                f"FAISS 向量数 ({faiss_ntotal}) 与 SQLite chunks 行数 ({chunks_count}) 不一致。"
                f"差值: {faiss_ntotal - chunks_count:+d}。建议重建索引。"
            )
        return {
            "aligned": aligned,
            "chunks_count": chunks_count,
            "faiss_vectors": faiss_ntotal,
            "detail": detail,
        }

    def get_chunk_ids_by_range(self, faiss_start: int, count: int) -> List[int]:
        """
        根据 FAISS 索引位置反查 chunks.id。

        约定: chunks 表按 AUTOINCREMENT 顺序写入，与 FAISS 的 0-based 索引一一对应。
        faiss_id = 0 对应 chunks 表中最早插入的那一行（最小 id）。

        Args:
            faiss_start: FAISS 索引起始位置（0-based）
            count:       需要查询的连续块数

        Returns:
            对应的 chunks.id 列表
        """
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT id FROM chunks ORDER BY id LIMIT ? OFFSET ?",
                (count, faiss_start),
            ).fetchall()
            return [r["id"] for r in rows]

    def get_chunk_by_id(self, chunk_id: int) -> dict | None:
        """根据 chunk ID 获取单个块的完整信息"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM chunks WHERE id = ?", (chunk_id,)
            ).fetchone()
            if row is None:
                return None
            result = dict(row)
            # 反序列化 metadata JSON
            if "metadata" in result and isinstance(result["metadata"], str):
                try:
                    result["metadata"] = json.loads(result["metadata"])
                except json.JSONDecodeError:
                    result["metadata"] = {}
            return result

    def chunk_exists(self, content_hash: str) -> bool:
        """
        检查是否已存在内容相同的块（去重）。

        Args:
            content_hash: 块内容的前 100 个字符作为简易哈希
        """
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM chunks WHERE content LIKE ?",
                (f"{content_hash}%",),
            ).fetchone()
            return row["cnt"] > 0
