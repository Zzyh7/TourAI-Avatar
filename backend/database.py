"""
数据库连接管理 —— SQLite + SQLAlchemy。
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import CONFIG


engine = create_engine(
    CONFIG.database_url,
    connect_args={"check_same_thread": False},  # SQLite 需要
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db():
    """创建所有表 + 自动迁移新增字段"""
    from models.schema import Session, Conversation, Document, DigitalHumanConfig, ScenicSpot, CommonDialogue  # noqa
    Base.metadata.create_all(bind=engine)

    # 自动迁移：为已存在的表添加新列（SQLite 不支持 ALTER TABLE ADD COLUMN IF NOT EXISTS）
    import sqlite3
    conn = engine.raw_connection()
    cursor = conn.cursor()
    try:
        # common_dialogues 新增 variants 字段
        cursor.execute("ALTER TABLE common_dialogues ADD COLUMN variants TEXT DEFAULT ''")
    except (sqlite3.OperationalError, Exception):
        pass  # 列已存在，忽略
    # conversations 新增 satisfaction 字段
    try:
        cursor.execute("ALTER TABLE conversations ADD COLUMN satisfaction VARCHAR(10) DEFAULT ''")
    except (sqlite3.OperationalError, Exception):
        pass
    # conversations 新增 is_unanswered 字段
    try:
        cursor.execute("ALTER TABLE conversations ADD COLUMN is_unanswered INTEGER DEFAULT 0")
    except (sqlite3.OperationalError, Exception):
        pass
    conn.commit()
    conn.close()


def get_db():
    """FastAPI 依赖注入: 获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
