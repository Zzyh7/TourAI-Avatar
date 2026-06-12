"""
SQLAlchemy 数据表定义。
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


def _gen_id() -> str:
    return uuid.uuid4().hex[:12]


class Session(Base):
    """对话会话"""
    __tablename__ = "sessions"

    id = Column(String(12), primary_key=True, default=_gen_id)
    visitor_tag = Column(String(50), default="")      # 家庭游/情侣游/文化深度游/休闲游
    created_at = Column(DateTime, default=datetime.utcnow)

    conversations = relationship("Conversation", back_populates="session", cascade="all, delete-orphan")


class Conversation(Base):
    """对话记录"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(12), ForeignKey("sessions.id"), nullable=False)
    role = Column(String(10), nullable=False)          # user / assistant
    content = Column(Text, nullable=False)
    sentiment = Column(String(10), default="")          # 正面/中性/负面
    latency_ms = Column(Integer, default=0)             # 响应延迟(毫秒)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="conversations")


class Document(Base):
    """知识库文档"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)      # pdf/docx/txt
    chunk_count = Column(Integer, default=0)
    size_bytes = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.utcnow)


class DigitalHumanConfig(Base):
    """数字人形象配置（单行）"""
    __tablename__ = "digital_human_config"

    id = Column(Integer, primary_key=True, default=1)
    live2d_model = Column(String(100), default="default")   # Live2D模型名
    voice_name = Column(String(50), default="zh-CN-XiaoxiaoNeural")  # Edge-TTS音色
    voice_speed = Column(Float, default=1.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ScenicSpot(Base):
    """预设景点信息"""
    __tablename__ = "scenic_spots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    latitude = Column(Float, default=0.0)
    longitude = Column(Float, default=0.0)
    trigger_radius = Column(Integer, default=100)       # GPS触发半径(米)
    description = Column(Text, default="")
    audio_intro_path = Column(String(255), default="")  # 预生成讲解音频路径
    category = Column(String(50), default="")            # 景点类别
    visit_duration = Column(Integer, default=60)         # 建议游览时间(分钟)
    created_at = Column(DateTime, default=datetime.utcnow)


class CommonDialogue(Base):
    """常用对话 —— 预设问答，命中后直接返回，不走 LLM 生成"""
    __tablename__ = "common_dialogues"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(Text, nullable=False)              # 触发问题
    answer = Column(Text, nullable=False)                # 预设回答
    keywords = Column(String(500), default="")           # 匹配关键词，逗号分隔
    variants = Column(Text, default="")                  # JSON数组，相似提问变体
    category = Column(String(50), default="一般")         # 分类标签
    priority = Column(Integer, default=0)                # 优先级，越高越优先
    enabled = Column(Integer, default=1)                 # 是否启用 0/1
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
