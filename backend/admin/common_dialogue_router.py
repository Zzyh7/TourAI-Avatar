"""
常用对话管理 API —— 增删改查 + 批量导入/导出。
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.schema import CommonDialogue

router = APIRouter(prefix="/api/admin/common-dialogues", tags=["常用对话管理"])


# ==================== Pydantic 模型 ====================

class CommonDialogueCreate(BaseModel):
    question: str = Field(..., description="触发问题")
    answer: str = Field(..., description="预设回答")
    keywords: str = ""                              # 逗号分隔关键词
    variants: str = ""                              # JSON数组，相似提问变体
    category: str = "一般"
    priority: int = 0
    enabled: int = 1


class CommonDialogueUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    keywords: Optional[str] = None
    variants: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[int] = None
    enabled: Optional[int] = None


class CommonDialogueBatchImport(BaseModel):
    items: list[CommonDialogueCreate] = Field(..., description="批量导入的对话列表")


class CommonDialogueOut(BaseModel):
    id: int
    question: str
    answer: str
    keywords: str
    category: str
    priority: int
    enabled: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ==================== CRUD 端点 ====================

@router.get("", response_model=list[CommonDialogueOut])
def list_dialogues(
    category: Optional[str] = Query(None, description="分类筛选"),
    enabled: Optional[int] = Query(None, description="启用状态 0/1"),
    search: Optional[str] = Query(None, description="搜索问题/答案/关键词"),
    db: Session = Depends(get_db),
):
    """获取常用对话列表，支持筛选和搜索"""
    q = db.query(CommonDialogue)

    if category:
        q = q.filter(CommonDialogue.category == category)
    if enabled is not None:
        q = q.filter(CommonDialogue.enabled == enabled)
    if search:
        like = f"%{search}%"
        q = q.filter(
            (CommonDialogue.question.like(like)) |
            (CommonDialogue.answer.like(like)) |
            (CommonDialogue.keywords.like(like))
        )

    return q.order_by(CommonDialogue.priority.desc(), CommonDialogue.id.desc()).all()


@router.post("", response_model=CommonDialogueOut)
def create_dialogue(data: CommonDialogueCreate, db: Session = Depends(get_db)):
    """新增一条常用对话"""
    dialogue = CommonDialogue(
        question=data.question,
        answer=data.answer,
        keywords=data.keywords,
        variants=data.variants,
        category=data.category,
        priority=data.priority,
        enabled=data.enabled,
    )
    db.add(dialogue)
    db.commit()
    db.refresh(dialogue)
    return dialogue


@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    """获取所有分类列表"""
    rows = db.query(CommonDialogue.category).distinct().all()
    return {"categories": [r[0] for r in rows if r[0]]}


@router.get("/{dialogue_id}", response_model=CommonDialogueOut)
def get_dialogue(dialogue_id: int, db: Session = Depends(get_db)):
    """获取单条常用对话"""
    dialogue = db.query(CommonDialogue).filter(CommonDialogue.id == dialogue_id).first()
    if not dialogue:
        return {"error": "对话不存在"}
    return dialogue


@router.put("/{dialogue_id}", response_model=CommonDialogueOut)
def update_dialogue(dialogue_id: int, data: CommonDialogueUpdate, db: Session = Depends(get_db)):
    """编辑一条常用对话"""
    dialogue = db.query(CommonDialogue).filter(CommonDialogue.id == dialogue_id).first()
    if not dialogue:
        return {"error": "对话不存在"}

    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(dialogue, key, value)
    dialogue.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(dialogue)
    return dialogue


@router.delete("/{dialogue_id}")
def delete_dialogue(dialogue_id: int, db: Session = Depends(get_db)):
    """删除一条常用对话"""
    dialogue = db.query(CommonDialogue).filter(CommonDialogue.id == dialogue_id).first()
    if not dialogue:
        return {"error": "对话不存在"}
    db.delete(dialogue)
    db.commit()
    return {"deleted": True, "id": dialogue_id}


# ==================== 批量操作 ====================

@router.post("/batch")
def batch_import(data: CommonDialogueBatchImport, db: Session = Depends(get_db)):
    """批量导入常用对话（用于后续导入对话数据）"""
    count = 0
    for item in data.items:
        dialogue = CommonDialogue(
            question=item.question,
            answer=item.answer,
            keywords=item.keywords,
            variants=getattr(item, 'variants', ''),
            category=item.category,
            priority=item.priority,
            enabled=item.enabled,
        )
        db.add(dialogue)
        count += 1
    db.commit()
    return {"imported": count, "message": f"成功导入 {count} 条常用对话"}


@router.get("/export/all", response_model=list[CommonDialogueOut])
def export_all(db: Session = Depends(get_db)):
    """导出全部常用对话（JSON 格式）"""
    return db.query(CommonDialogue).order_by(CommonDialogue.id).all()
