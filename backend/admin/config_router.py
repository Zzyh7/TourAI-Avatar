"""
数字人形象配置 API —— 形象/音色切换。
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.schema import DigitalHumanConfig

router = APIRouter(prefix="/api/admin/config", tags=["数字人配置"])


class DigitalHumanConfigUpdate(BaseModel):
    live2d_model: str = "default"
    voice_name: str = "BV700_streaming"  # 豆包 TTS 默认音色 (灿灿2.0女声)
    voice_speed: float = 1.0


def _get_or_create_config(db: Session) -> DigitalHumanConfig:
    """获取或创建配置（单行表）"""
    config = db.query(DigitalHumanConfig).first()
    if config is None:
        config = DigitalHumanConfig(id=1)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.get("/digital-human")
def get_config(db: Session = Depends(get_db)):
    """获取数字人当前配置"""
    config = _get_or_create_config(db)
    return {
        "live2d_model": config.live2d_model,
        "voice_name": config.voice_name,
        "voice_speed": config.voice_speed,
        "updated_at": config.updated_at.isoformat() if config.updated_at else None,
    }


@router.put("/digital-human")
def update_config(data: DigitalHumanConfigUpdate, db: Session = Depends(get_db)):
    """更新数字人配置"""
    config = _get_or_create_config(db)
    config.live2d_model = data.live2d_model
    config.voice_name = data.voice_name
    config.voice_speed = data.voice_speed
    db.commit()
    db.refresh(config)
    return {
        "live2d_model": config.live2d_model,
        "voice_name": config.voice_name,
        "voice_speed": config.voice_speed,
        "message": "配置已更新"
    }
