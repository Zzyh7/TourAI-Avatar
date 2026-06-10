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
    """创建所有表"""
    from models.schema import Session, Conversation, Document, DigitalHumanConfig, ScenicSpot  # noqa
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI 依赖注入: 获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
