"""
配置中心 —— 全局管理环境变量、LLM实例、MCP连接、TTS/RAG参数。
"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv, find_dotenv

# 优先从项目根目录加载 .env (兼容从 backend/ 或项目根启动)
load_dotenv(find_dotenv(usecwd=True))


@dataclass
class Config:
    """全局配置单例"""

    # ==================== LLM — 主对话模型 (DeepSeek) ====================
    deepseek_api_key: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", "")
    )
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    deepseek_temperature: float = 0.7

    # ==================== LLM — 多模态模型 (通义千问-VL) ====================
    dashscope_api_key: str = field(
        default_factory=lambda: os.getenv("DASHSCOPE_API_KEY", "")
    )
    qwen_vl_model: str = "qwen-vl-max"

    # ==================== 高德地图 MCP ====================
    mcp_transport: str = "sse"
    mcp_url: str = field(
        default_factory=lambda: f"https://mcp.amap.com/sse?key={os.getenv('AMAP_API_KEY', '')}"
    )

    # 工具领域映射
    tool_domains: dict = field(default_factory=lambda: {
        "poi":     ["maps_text_search", "maps_search_detail"],
        "weather": ["maps_weather"],
        "route":   [
            "maps_direction_walking_by_address",
            "maps_direction_driving_by_address",
            "maps_direction_transit_integrated_by_address",
        ],
        "around":  ["maps_around_search"],
        "geo":     ["maps_geo", "maps_regeocode"],
    })

    # ==================== 豆包 TTS (Seed-TTS-2.0 / 火山引擎 WebSocket V3) ====================
    doubao_tts_api_key: str = field(
        default_factory=lambda: os.getenv("DOUBAO_TTS_API_KEY", "")
    )
    doubao_tts_appid: str = field(
        default_factory=lambda: os.getenv("DOUBAO_TTS_APPID", "default")
    )
    doubao_tts_v1_api_key: str = field(
        default_factory=lambda: os.getenv("DOUBAO_TTS_V1_API_KEY", "")
    )  # V1 HTTP fallback 专用 Key（支持 mars_bigtts 中文音色）
    doubao_tts_voice: str = field(
        default_factory=lambda: os.getenv("DOUBAO_TTS_VOICE", "zh_male_tiancaitongsheng_mars_bigtts")
    )  # 天才童声 (男)
    doubao_tts_speed_ratio: float = 1.0              # 语速 1.0=正常，会自动转为 speech_rate (-50~100)

    # 向后兼容：Edge-TTS 配置（切换时保留）
    tts_voice: str = "zh-CN-XiaoxiaoNeural"
    tts_rate: str = "+10%"
    tts_pitch: str = "+0Hz"

    # ==================== RAG 参数 ====================
    chunk_size: int = 500
    chunk_overlap: int = 100
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    vector_store_path: str = "data/vector_db"
    doc_store_path: str = "data/docs"
    retrieval_top_k: int = 5    # 检索返回片段数

    # ==================== 数据库 ====================
    database_url: str = "sqlite:///data/travel_agent.db"

    # ==================== 自动校验 ====================
    def __post_init__(self):
        """启动时校验关键配置 + 注入环境变量"""
        if not self.deepseek_api_key:
            raise ValueError("请配置 DEEPSEEK_API_KEY")
        if self.dashscope_api_key:
            os.environ["DASHSCOPE_API_KEY"] = self.dashscope_api_key
        if self.deepseek_api_key:
            os.environ["DEEPSEEK_API_KEY"] = self.deepseek_api_key

    def create_llm(self):
        """创建 DeepSeek 对话模型实例 (OpenAI 兼容接口)"""
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=self.deepseek_model,
            api_key=self.deepseek_api_key,
            base_url=self.deepseek_base_url,
            temperature=self.deepseek_temperature,
            streaming=True,
        )

    def create_multimodal_llm(self):
        """创建通义千问-VL 多模态模型实例"""
        from langchain_community.chat_models.tongyi import ChatTongyi
        return ChatTongyi(
            model=self.qwen_vl_model,
            api_key=self.dashscope_api_key,
            streaming=True,
        )


CONFIG = Config()
