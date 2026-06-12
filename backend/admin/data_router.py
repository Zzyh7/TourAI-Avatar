"""
数据管理 API —— 会话 / 对话记录 查看与管理。
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.schema import Session as SessionModel, Conversation

router = APIRouter(prefix="/api/admin/data", tags=["数据管理"])


# ==================== Pydantic 模型 ====================

class ConversationOut(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    sentiment: str
    latency_ms: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionOut(BaseModel):
    id: str
    visitor_tag: str
    created_at: datetime
    conversation_count: int = 0

    model_config = {"from_attributes": True}


class SessionDetail(SessionOut):
    conversations: list[ConversationOut] = []


# ==================== 会话管理 ====================

@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(
    search: Optional[str] = Query(None, description="搜索会话ID"),
    tag: Optional[str] = Query(None, description="按游客标签筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
):
    """获取会话列表"""
    q = db.query(SessionModel)
    if search:
        q = q.filter(SessionModel.id.like(f"%{search}%"))
    if tag:
        q = q.filter(SessionModel.visitor_tag == tag)

    total = q.count()
    sessions = (
        q.order_by(SessionModel.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    result = []
    for s in sessions:
        count = db.query(Conversation).filter(Conversation.session_id == s.id).count()
        result.append(SessionOut(
            id=s.id,
            visitor_tag=s.visitor_tag,
            created_at=s.created_at,
            conversation_count=count,
        ))

    # 通过 header 返回总数供前端分页
    return result


@router.get("/sessions/count")
def session_count(db: Session = Depends(get_db)):
    """获取会话总数"""
    total = db.query(SessionModel).count()
    return {"total": total}


@router.get("/sessions/{session_id}", response_model=SessionDetail)
def get_session_detail(session_id: str, db: Session = Depends(get_db)):
    """获取会话详情（含对话记录）"""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        return {"error": "会话不存在"}

    conversations = (
        db.query(Conversation)
        .filter(Conversation.session_id == session_id)
        .order_by(Conversation.created_at.asc())
        .all()
    )

    return SessionDetail(
        id=session.id,
        visitor_tag=session.visitor_tag,
        created_at=session.created_at,
        conversation_count=len(conversations),
        conversations=[ConversationOut.model_validate(c) for c in conversations],
    )


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    """删除会话及其所有对话记录"""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        return {"error": "会话不存在"}
    db.delete(session)  # cascade 删除关联的 conversations
    db.commit()
    return {"deleted": True, "id": session_id}


# ==================== 对话记录管理 ====================

@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(
    session_id: Optional[str] = Query(None, description="按会话ID筛选"),
    role: Optional[str] = Query(None, description="按角色筛选 (user/assistant)"),
    sentiment: Optional[str] = Query(None, description="按情感筛选"),
    search: Optional[str] = Query(None, description="搜索对话内容"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """获取对话记录列表"""
    q = db.query(Conversation)
    if session_id:
        q = q.filter(Conversation.session_id == session_id)
    if role:
        q = q.filter(Conversation.role == role)
    if sentiment:
        q = q.filter(Conversation.sentiment == sentiment)
    if search:
        q = q.filter(Conversation.content.like(f"%{search}%"))

    return (
        q.order_by(Conversation.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )


@router.get("/conversations/count")
def conversation_count(db: Session = Depends(get_db)):
    """获取对话总数"""
    total = db.query(Conversation).count()
    return {"total": total}


@router.delete("/conversations/{conv_id}")
def delete_conversation(conv_id: int, db: Session = Depends(get_db)):
    """删除单条对话记录"""
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        return {"error": "对话不存在"}
    db.delete(conv)
    db.commit()
    return {"deleted": True, "id": conv_id}
