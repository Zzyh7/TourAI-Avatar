"""
RAG 系统独立启动脚本 —— 用于测试和独立部署。

启动方式:
    cd backend
    python -m rag_system.main

    或:
    uvicorn rag_system.main:app --host 0.0.0.0 --port 8001 --reload

此文件演示如何将 RAG 路由挂载到 FastAPI 应用。
生产环境中，建议在 backend/main.py 中通过 app.include_router() 集成。
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router as rag_router
from . import init_rag


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时预加载所有 RAG 服务"""
    init_rag()
    yield
    print("👋 RAG 服务关闭")


app = FastAPI(
    title="RAG 知识库服务",
    description="景区导览数字人 — 混合检索 (FAISS + BM25 + RRF) 知识库",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载 RAG 路由
app.include_router(rag_router, prefix="/api/rag")


@app.get("/")
def root():
    return {
        "service": "RAG知识库",
        "docs": "/docs",
        "endpoints": {
            "upload": "POST /api/rag/admin/upload",
            "query": "POST /api/rag/query",
            "faq_import": "POST /api/rag/admin/faq/import",
            "faq_import_csv": "POST /api/rag/admin/faq/import-csv",
            "stats": "GET /api/rag/admin/stats",
            "documents": "GET /api/rag/admin/documents",
            "health": "GET /api/rag/health",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("rag_system.main:app", host="0.0.0.0", port=8001, reload=True)
