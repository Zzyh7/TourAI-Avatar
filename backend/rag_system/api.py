"""
RAG 知识库 API —— FastAPI 路由。

端点:
  POST /api/rag/admin/upload              — 上传文档 (PDF/Word/TXT/MD)
  POST /api/rag/query                     — 知识问答
  POST /api/rag/admin/faq/import          — 批量导入 FAQ 问答对
  POST /api/rag/admin/import-dialogues    — 将常用对话导入为知识库文档块
  GET  /api/rag/admin/stats               — 索引统计信息
  GET  /api/rag/admin/documents           — 已上传文档列表
  DELETE /api/rag/admin/documents/{doc_id} — 删除文档
"""
import os
import json
import csv
import io
import time
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from pydantic import BaseModel

from .config import rag_config
from .embedding import EmbeddingService
from .splitter import TextSplitter
from .loader import DocumentLoader, EXT_TO_TYPE
from .document_store import DocumentStore
from .hybrid_retriever import HybridRetriever

# ==================== 全局服务实例 ====================

# 模块级单例（在首次使用时懒加载）
_embedder: EmbeddingService | None = None
_retriever: HybridRetriever | None = None
_doc_store: DocumentStore | None = None
_splitter: TextSplitter | None = None


def get_embedder() -> EmbeddingService:
    global _embedder
    if _embedder is None:
        print("... 正在加载 BGE 嵌入模型...")
        _embedder = EmbeddingService()
        print("[OK] BGE 嵌入模型就绪")
    return _embedder


def get_retriever() -> HybridRetriever:
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever(get_embedder())
        # 启动时校验 FAISS ↔ SQLite 对齐（如果 doc_store 也已初始化）
        _validate_startup_alignment()
    return _retriever


def get_doc_store() -> DocumentStore:
    global _doc_store
    if _doc_store is None:
        _doc_store = DocumentStore()
        # 启动时校验 FAISS ↔ SQLite 对齐（如果 retriever 也已初始化）
        _validate_startup_alignment()
    return _doc_store


def _validate_startup_alignment():
    """启动时校验 FAISS 向量数与 SQLite chunks 行数是否对齐"""
    global _retriever, _doc_store
    if _retriever is None or _doc_store is None:
        return
    faiss_ntotal = _retriever.stats.get("faiss_vectors", 0)
    alignment = _doc_store.validate_faiss_alignment(faiss_ntotal)
    if alignment["aligned"]:
        print(f"[OK] FAISS/SQLite 对齐校验通过 ({alignment['faiss_vectors']} 个向量, {alignment['chunks_count']} 个块)")
    else:
        print(f"[WARN] {alignment['detail']}")


def get_splitter() -> TextSplitter:
    global _splitter
    if _splitter is None:
        _splitter = TextSplitter()
    return _splitter


# ==================== FastAPI 路由 ====================

# 使用 prefix，由挂载方决定最终路径
# 建议: app.include_router(rag_router, prefix="/api/rag")
router = APIRouter(tags=["RAG知识库"])


# ==================== 请求/响应模型 ====================

class QueryRequest(BaseModel):
    question: str
    top_k: int = 5


class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    from_faq: bool = False
    below_threshold: bool = False


class FAQItem(BaseModel):
    question: str
    answer: str


class FAQImportRequest(BaseModel):
    faq_pairs: List[FAQItem]


class StatsResponse(BaseModel):
    faiss_vectors: int
    bm25_documents: int
    faq_pairs: int
    faq_answers: int
    documents_count: int
    chunks_count: int


# ==================== 管理端点 ====================

@router.post("/admin/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    上传景区知识库文档 (PDF/Word/TXT/Markdown)。

    处理流程:
      1. 校验文件格式
      2. 保存到本地文档库
      3. 解析文本内容
      4. 分块 (chunk_size=500, overlap=50)
      5. 先写入 SQLite（获取 chunk_id，确保 FAISS 索引 ID 对齐）
      6. 将 chunk_id + embedding_model 标记到每个块
      7. 向量化并存入 FAISS + BM25 索引
      8. 校验 FAISS 与 SQLite 对齐
      9. 持久化所有索引到磁盘

    返回:
      {
        "id": doc_id,
        "chunk_ids": [1, 2, ...],
        "filename": "...",
        "file_type": "pdf",
        "chunk_count": 15,
        "embedding_model": "BAAI/bge-small-zh-v1.5",
        "faiss_aligned": true,
        "message": "上传成功，已处理 15 个文本块"
      }
    """
    # 1. 校验文件类型
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件名")

    _, ext = os.path.splitext(file.filename)
    ext = ext.lower()
    if ext not in (".pdf", ".docx", ".txt", ".md"):
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {ext}，仅支持 PDF/Word/TXT/Markdown",
        )

    file_type = EXT_TO_TYPE.get(ext, ext.lstrip("."))

    # 2. 保存文件到本地
    doc_store_path = rag_config.doc_store_path
    os.makedirs(doc_store_path, exist_ok=True)
    save_path = os.path.join(doc_store_path, file.filename)

    content_bytes = await file.read()
    with open(save_path, "wb") as f:
        f.write(content_bytes)

    # 3. 解析文档
    try:
        docs = DocumentLoader.load(save_path)
    except Exception as e:
        # 清理已保存的文件
        if os.path.exists(save_path):
            os.remove(save_path)
        raise HTTPException(status_code=500, detail=f"文档解析失败: {str(e)}")

    if not docs:
        if os.path.exists(save_path):
            os.remove(save_path)
        raise HTTPException(status_code=400, detail="文档内容为空，未能提取到文本")

    # 4. 分块
    splitter = get_splitter()
    chunks = splitter.split_documents(docs)

    if not chunks:
        raise HTTPException(status_code=400, detail="分块后无有效内容")

    # 5. 先记录元数据到 SQLite（获取 chunk_id，确保与 FAISS 索引 ID 对齐）
    doc_store = get_doc_store()
    doc_id, chunk_ids = doc_store.add_document(
        filename=file.filename,
        file_type=file_type,
        chunks=chunks,
        size_bytes=len(content_bytes),
    )

    # 6. 将 chunk_id 和 embedding_model 写入每个 chunk 的 metadata，
    #    这样存入 FAISS/BM25 后可反查 SQLite 元数据
    embedder = get_embedder()
    for chunk, cid in zip(chunks, chunk_ids):
        chunk.metadata["chunk_id"] = cid
        chunk.metadata["embedding_model"] = embedder.model_name

    # 7. 向量化并存入 FAISS + BM25 索引（此时 chunk 已携带 SQLite ID）
    retriever = get_retriever()
    retriever.add_documents(chunks)

    # 8. 校验 FAISS 与 SQLite 对齐
    alignment = doc_store.validate_faiss_alignment(
        retriever.stats["faiss_vectors"]
    )
    if not alignment["aligned"]:
        print(f"[WARN] FAISS/SQLite 对齐警告: {alignment['detail']}")

    return {
        "id": doc_id,
        "chunk_ids": chunk_ids,
        "filename": file.filename,
        "file_type": file_type,
        "chunk_count": len(chunks),
        "size_bytes": len(content_bytes),
        "embedding_model": embedder.model_name,
        "faiss_aligned": alignment["aligned"],
        "message": f"上传成功，已处理 {len(chunks)} 个文本块",
    }


@router.get("/admin/documents")
def list_documents():
    """获取已上传文档列表"""
    doc_store = get_doc_store()
    docs = doc_store.get_all_documents()
    return {"documents": docs, "total": len(docs)}


@router.delete("/admin/documents/{doc_id}")
def delete_document(doc_id: int):
    """
    删除文档（数据库记录 + 本地文件）。

    注意：此操作不会从 FAISS/BM25 索引中移除对应的向量。
    如需完全清理，建议重建索引。
    """
    doc_store = get_doc_store()
    doc = doc_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 删除本地文件
    file_path = os.path.join(rag_config.doc_store_path, doc["filename"])
    if os.path.exists(file_path):
        os.remove(file_path)

    # 删除数据库记录（级联删除关联的 chunks）
    doc_store.delete_document(doc_id)

    return {"message": f"文档 '{doc['filename']}' 已删除（注意：FAISS/BM25索引中的向量需重建索引才能完全移除）"}


@router.get("/admin/stats")
def get_stats():
    """获取知识库统计信息"""
    retriever = get_retriever()
    doc_store = get_doc_store()

    retriever_stats = retriever.stats
    return StatsResponse(
        faiss_vectors=retriever_stats["faiss_vectors"],
        bm25_documents=retriever_stats["bm25_documents"],
        faq_pairs=retriever_stats["faq_pairs"],
        faq_answers=retriever_stats["faq_answers"],
        documents_count=doc_store.get_document_count(),
        chunks_count=doc_store.get_chunk_count(),
    )


# ==================== FAQ 导入 ====================

@router.post("/admin/faq/import")
async def import_faq(request: FAQImportRequest):
    """
    批量导入 FAQ 问答对（JSON 格式）。

    请求体示例:
    {
      "faq_pairs": [
        {"question": "景区开放时间？", "answer": "景区每日8:00-17:30开放。"},
        {"question": "门票价格是多少？", "answer": "成人票80元，学生票半价。"}
      ]
    }
    """
    if not request.faq_pairs:
        raise HTTPException(status_code=400, detail="FAQ 列表为空")

    faq_dicts = [{"question": item.question, "answer": item.answer} for item in request.faq_pairs]

    retriever = get_retriever()
    retriever.import_faq(faq_dicts)

    return {
        "message": f"成功导入 {len(faq_dicts)} 个 FAQ 问答对",
        "count": len(faq_dicts),
    }


@router.post("/admin/faq/import-csv")
async def import_faq_csv(file: UploadFile = File(...)):
    """
    从 CSV 文件批量导入 FAQ 问答对。

    CSV 格式要求:
      - 第一列为问题 (question)
      - 第二列为答案 (answer)
      - 第一行为表头（会被跳过）
      - 编码: UTF-8
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="请上传 CSV 文件")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("gbk")  # 回退到 GBK 编码

    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if len(rows) < 2:
        raise HTTPException(status_code=400, detail="CSV 内容为空或格式不正确")

    # 跳过表头
    faq_dicts = []
    for row in rows[1:]:
        if len(row) >= 2 and row[0].strip() and row[1].strip():
            faq_dicts.append({"question": row[0].strip(), "answer": row[1].strip()})

    if not faq_dicts:
        raise HTTPException(status_code=400, detail="CSV 中无有效数据")

    retriever = get_retriever()
    retriever.import_faq(faq_dicts)

    return {
        "message": f"成功从CSV导入 {len(faq_dicts)} 个FAQ问答对",
        "count": len(faq_dicts),
    }


# ==================== 常用对话导入知识库 ====================

class DialogueItem(BaseModel):
    question: str
    answer: str


class DialogueImportRequest(BaseModel):
    items: List[DialogueItem]


@router.post("/admin/import-dialogues")
async def import_dialogues(request: DialogueImportRequest):
    """
    将常用对话内容导入知识库（作为文档块存入 FAISS/BM25 索引）。

    与 FAQ 导入不同：FAQ 是精确匹配后直接返回预设答案；
    此接口将对话文本分块向量化后存入主文档索引，
    在 RAG 检索时作为参考资料提供给 LLM 生成答案。

    请求体示例:
    {
      "items": [
        {"question": "景区开放时间？", "answer": "景区每日8:00-17:30开放。"},
        {"question": "门票价格是多少？", "answer": "成人票80元，学生票半价。"}
      ]
    }
    """
    if not request.items:
        raise HTTPException(status_code=400, detail="对话列表为空")

    # 将每个对话转为文本文档
    from langchain_core.documents import Document as LCDocument
    docs = []
    for item in request.items:
        text = f"问题：{item.question}\n回答：{item.answer}"
        docs.append(LCDocument(
            page_content=text,
            metadata={"source": "常用对话导入", "type": "dialogue"},
        ))

    # 分块
    splitter = get_splitter()
    chunks = splitter.split_documents(docs)

    if not chunks:
        raise HTTPException(status_code=400, detail="分块后无有效内容")

    # 写入 SQLite 文档记录（标记为虚拟文档）
    doc_store = get_doc_store()
    doc_id, chunk_ids = doc_store.add_document(
        filename="【常用对话导入】",
        file_type="dialogues",
        chunks=chunks,
        size_bytes=0,
    )

    # 标记 chunk_id 和 embedding_model
    embedder = get_embedder()
    for chunk, cid in zip(chunks, chunk_ids):
        chunk.metadata["chunk_id"] = cid
        chunk.metadata["embedding_model"] = embedder.model_name

    # 向量化并存入 FAISS + BM25 索引
    retriever = get_retriever()
    retriever.add_documents(chunks)

    # 对齐校验
    alignment = doc_store.validate_faiss_alignment(
        retriever.stats["faiss_vectors"]
    )
    if not alignment["aligned"]:
        print(f"[WARN] 导入对话后 FAISS/SQLite 对齐警告: {alignment['detail']}")

    return {
        "message": f"成功将 {len(request.items)} 条常用对话导入知识库（{len(chunks)} 个文本块）",
        "dialogue_count": len(request.items),
        "chunk_count": len(chunks),
        "faiss_aligned": alignment["aligned"],
    }


# ==================== 问答端点 ====================

@router.post("/query")
async def query(request: QueryRequest):
    """
    知识问答 —— 混合检索 + LLM 生成。

    处理流程:
      1. FAQ 精确匹配（如果命中，直接返回预写答案）
      2. FAISS 向量检索 (top_k=10) + BM25 关键词检索 (top_k=10)
      3. RRF 融合 → 取 top 5
      4. 分数阈值检查（低于 0.6 触发"资料不足"）
      5. 调用 LLM 生成最终答案
      6. 返回答案 + 引用来源

    请求体:
      {"question": "西湖有什么历史典故？", "top_k": 5}

    返回:
      {"answer": "...", "sources": ["景区介绍.pdf"], "from_faq": false}
    """
    start_time = time.time()

    # 1. 检查知识库是否就绪
    retriever = get_retriever()
    if not retriever.is_ready:
        return QueryResponse(
            answer="知识库尚未初始化，请先通过管理后台上传文档。",
            sources=[],
            below_threshold=True,
        )

    # 2. 混合检索
    result = retriever.retrieve(request.question, top_k=request.top_k)

    # 3. 如果来自 FAQ，直接返回
    if result["from_faq"]:
        elapsed = int((time.time() - start_time) * 1000)
        return QueryResponse(
            answer=result["faq_answer"],
            sources=result["sources"],
            from_faq=True,
        )

    # 4. 如果低于阈值，返回"不知道"
    if result["below_threshold"]:
        elapsed = int((time.time() - start_time) * 1000)
        return QueryResponse(
            answer=(
                "抱歉，关于这个问题我暂时还不太了解。"
                "资料库中暂无相关信息，建议您咨询景区工作人员或查阅官方资料。"
            ),
            sources=[],
            below_threshold=True,
        )

    # 5. 拼接上下文
    context = "\n---\n".join(doc.page_content for doc in result["docs"])

    # 6. 调用 LLM 生成答案
    answer = await _generate_answer(request.question, context, result["docs"])

    elapsed = int((time.time() - start_time) * 1000)
    print(f"[OK] 问答完成 ({elapsed}ms): {request.question[:50]}...")

    return QueryResponse(
        answer=answer,
        sources=result["sources"],
    )


# ==================== LLM 生成 ====================

async def _generate_answer(
    question: str, context: str, docs: list
) -> str:
    """
    调用 LLM 基于检索上下文生成答案。

    优先使用 DeepSeek (OpenAI 兼容接口)，
    如果 API Key 未配置则直接返回检索到的原始上下文。
    """
    api_key = rag_config.llm_api_key

    if not api_key:
        # 无 LLM 配置：直接返回最相关的上下文块
        return (
            f"（未配置 LLM，以下为检索到的相关内容）\n\n{context}"
            if context
            else "未找到相关内容。"
        )

    prompt = rag_config.rag_prompt_template.format(
        question=question, context=context
    )

    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=rag_config.llm_model,
            api_key=api_key,
            base_url=rag_config.llm_base_url,
            temperature=rag_config.llm_temperature,
        )

        response = await llm.ainvoke(prompt)
        return response.content.strip()

    except ImportError:
        # langchain_openai 未安装
        return (
            f"（langchain_openai 未安装，以下为检索到的相关内容）\n\n{context}"
            if context
            else "未找到相关内容。"
        )
    except Exception as e:
        # LLM 调用失败，返回上下文作为降级
        print(f"[WARN] LLM 生成失败: {e}")
        return (
            f"（LLM 服务暂时不可用: {str(e)[:100]}）\n\n"
            f"以下为检索到的参考资料：\n\n{context}"
            if context
            else "LLM 服务暂时不可用，且未找到相关内容。"
        )


# ==================== 健康检查 ====================

@router.get("/health")
def health():
    """RAG 服务健康检查"""
    retriever = get_retriever()
    return {
        "status": "ok",
        "ready": retriever.is_ready,
        "stats": retriever.stats,
    }
