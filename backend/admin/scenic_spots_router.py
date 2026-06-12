"""
景点管理 API —— 增删改查。
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.schema import ScenicSpot

router = APIRouter(prefix="/api/admin/scenic-spots", tags=["景点管理"])


# ==================== Pydantic 模型 ====================

class ScenicSpotCreate(BaseModel):
    name: str = Field(..., description="景点名称")
    latitude: float = 0.0
    longitude: float = 0.0
    trigger_radius: int = 100
    description: str = ""
    audio_intro_path: str = ""
    category: str = ""
    visit_duration: int = 60


class ScenicSpotUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    trigger_radius: Optional[int] = None
    description: Optional[str] = None
    audio_intro_path: Optional[str] = None
    category: Optional[str] = None
    visit_duration: Optional[int] = None


class ScenicSpotOut(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float
    trigger_radius: int
    description: str
    audio_intro_path: str
    category: str
    visit_duration: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ==================== CRUD 端点 ====================

@router.get("", response_model=list[ScenicSpotOut])
def list_spots(
    category: Optional[str] = Query(None, description="分类筛选"),
    search: Optional[str] = Query(None, description="搜索景点名称"),
    db: Session = Depends(get_db),
):
    """获取景点列表"""
    q = db.query(ScenicSpot)
    if category:
        q = q.filter(ScenicSpot.category == category)
    if search:
        q = q.filter(ScenicSpot.name.like(f"%{search}%"))
    return q.order_by(ScenicSpot.id.desc()).all()


@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    """获取所有景点分类"""
    rows = db.query(ScenicSpot.category).distinct().all()
    return {"categories": [r[0] for r in rows if r[0]]}


@router.post("", response_model=ScenicSpotOut)
def create_spot(data: ScenicSpotCreate, db: Session = Depends(get_db)):
    """新增景点"""
    spot = ScenicSpot(**data.model_dump())
    db.add(spot)
    db.commit()
    db.refresh(spot)
    return spot


@router.get("/{spot_id}", response_model=ScenicSpotOut)
def get_spot(spot_id: int, db: Session = Depends(get_db)):
    """获取单个景点"""
    spot = db.query(ScenicSpot).filter(ScenicSpot.id == spot_id).first()
    if not spot:
        return {"error": "景点不存在"}
    return spot


@router.put("/{spot_id}", response_model=ScenicSpotOut)
def update_spot(spot_id: int, data: ScenicSpotUpdate, db: Session = Depends(get_db)):
    """编辑景点"""
    spot = db.query(ScenicSpot).filter(ScenicSpot.id == spot_id).first()
    if not spot:
        return {"error": "景点不存在"}
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(spot, key, value)
    db.commit()
    db.refresh(spot)
    return spot


@router.delete("/{spot_id}")
def delete_spot(spot_id: int, db: Session = Depends(get_db)):
    """删除景点"""
    spot = db.query(ScenicSpot).filter(ScenicSpot.id == spot_id).first()
    if not spot:
        return {"error": "景点不存在"}
    db.delete(spot)
    db.commit()
    return {"deleted": True, "id": spot_id}
