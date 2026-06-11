"""
RAG 系统配置 —— 集中管理所有参数。
路径基于项目根目录 (d:/TravelAgent)，适配 Docker 和本地运行。
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

# 加载 .env 文件中的环境变量
from dotenv import load_dotenv
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)

# HuggingFace 模型已缓存本地，使用离线模式避免每次启动联网验证
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

# 项目根目录: rag_system -> backend -> project_root
ROOT_DIR = Path(__file__).resolve().parent.parent.parent


@dataclass
class RAGConfig:
    """RAG 系统全局配置单例"""

    # ==================== 文本分割参数 ====================
    chunk_size: int = 500            # 每个块的最大字符数
    chunk_overlap: int = 50          # 相邻块之间的重叠字符数

    # ==================== 嵌入模型 ====================
    embedding_model: str = "BAAI/bge-small-zh-v1.5"  # BGE 中文小模型
    embedding_device: str = "cpu"                     # CPU 运行（如需 GPU 改为 "cuda"）

    # ==================== 数据存储路径 ====================
    data_root: str = field(
        default_factory=lambda: str(ROOT_DIR / "data" / "rag_data")
    )
    vector_store_path: str = field(
        default_factory=lambda: str(ROOT_DIR / "data" / "rag_data" / "vector_db")
    )
    doc_store_path: str = field(
        default_factory=lambda: str(ROOT_DIR / "data" / "rag_data" / "docs")
    )
    db_path: str = field(
        default_factory=lambda: str(ROOT_DIR / "data" / "rag_data" / "chunks.db")
    )
    bm25_corpus_path: str = field(
        default_factory=lambda: str(ROOT_DIR / "data" / "rag_data" / "vector_db" / "bm25_corpus.json")
    )
    faq_index_path: str = field(
        default_factory=lambda: str(ROOT_DIR / "data" / "rag_data" / "vector_db" / "faq")
    )

    # ==================== 检索参数 ====================
    retrieval_top_k: int = 10        # 每种检索方式各自返回的候选数
    final_top_k: int = 5             # RRF 融合后最终返回给 LLM 的块数
    score_threshold: float = 0.35    # FAISS 余弦相似度最低阈值（BGE 模型 0.3-0.4 仍有相关性）
    faq_threshold: float = 0.85      # FAQ 精确匹配的更高阈值
    rrf_k: int = 60                  # RRF 融合常数 k（经典值 60，平衡排名差异）

    # ==================== LLM 生成参数 ====================
    llm_api_key: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", "")
    )
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"
    llm_temperature: float = 0.7

    # ==================== Prompt 模板 ====================
    rag_prompt_template: str = (
        '你是一个专业的景区导览数字人。请基于【参考资料】回答问题。\n'
        '如果参考资料不足以回答，请直接说「资料中没有相关信息」，不要编造。\n\n'
        '【用户问题】：{question}\n\n'
        '【参考资料】：\n{context}'
    )

    def __post_init__(self):
        """确保所有目录存在"""
        os.makedirs(self.vector_store_path, exist_ok=True)
        os.makedirs(self.doc_store_path, exist_ok=True)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)


# 全局单例
rag_config = RAGConfig()
