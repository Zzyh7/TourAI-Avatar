"""
知识库管理 API —— 文档上传 / 删除 / 列表。
"""
import os
import shutil
from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.schema import Document
from services.rag.loader import DocumentLoader
from services.rag.splitter import TextSplitter
from config import CONFIG

router = APIRouter(prefix="/api/admin/knowledge", tags=["知识库管理"])


# 全局 RAG 服务引用（由 main.py 注入）
_rag_services = {"vector_store": None, "retriever": None}


def set_rag_services(vector_store, retriever):
    """注入 RAG 服务实例"""
    _rag_services["vector_store"] = vector_store
    _rag_services["retriever"] = retriever


def get_rag_services():
    return _rag_services["vector_store"], _rag_services["retriever"]


@router.post("/upload")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    上传景区知识库文档 (PDF/Word/TXT)。
    自动完成: 文本提取 → 分块 → 向量化 → 存入FAISS。
    """
    # 1. 校验文件类型
    _, ext = os.path.splitext(file.filename or "")
    ext = ext.lower()
    if ext not in (".pdf", ".docx", ".txt"):
        return {"error": f"不支持的文件格式: {ext}，仅支持 PDF/Word/TXT"}

    # 2. 保存文件
    os.makedirs(CONFIG.doc_store_path, exist_ok=True)
    save_path = os.path.join(CONFIG.doc_store_path, file.filename)
    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # 3. 加载文档内容
    try:
        docs = DocumentLoader.load(save_path)
    except Exception as e:
        return {"error": f"文档解析失败: {str(e)}"}

    # 4. 分块
    splitter = TextSplitter()
    chunks = splitter.split(docs)

    # 5. 向量化并存入FAISS
    vector_store, retriever = get_rag_services()
    if vector_store is not None:
        vector_store.add_documents(chunks)
        vector_store.save()
    if retriever is not None:
        retriever.set_documents(retriever._bm25_docs + chunks)

    # 6. 记录到数据库
    doc_record = Document(
        filename=file.filename,
        file_type=ext.replace(".", ""),
        chunk_count=len(chunks),
        size_bytes=len(content),
    )
    db.add(doc_record)
    db.commit()
    db.refresh(doc_record)

    return {
        "id": doc_record.id,
        "filename": file.filename,
        "file_type": ext,
        "chunk_count": len(chunks),
        "message": f"上传成功，已处理 {len(chunks)} 个文本块"
    }


@router.get("/list")
def list_documents(db: Session = Depends(get_db)):
    """获取已上传文档列表"""
    docs = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "file_type": d.file_type,
            "chunk_count": d.chunk_count,
            "size_bytes": d.size_bytes,
            "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
        }
        for d in docs
    ]


@router.delete("/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    """删除文档（数据库记录 + 文件）"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if doc is None:
        return {"error": "文档不存在"}

    # 删除文件
    file_path = os.path.join(CONFIG.doc_store_path, doc.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    db.delete(doc)
    db.commit()

    return {"message": f"文档 '{doc.filename}' 已删除"}
