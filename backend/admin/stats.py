"""
数据统计 API —— 大屏数据 / 热门问答 / 情感趋势。
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models.schema import Conversation, Session as SessionModel

router = APIRouter(prefix="/api/admin/stats", tags=["数据统计"])


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    """获取总览数据（服务人次、满意度、平均延迟）"""
    total_sessions = db.query(func.count(SessionModel.id)).scalar() or 0
    total_conversations = db.query(func.count(Conversation.id)).scalar() or 0

    # 满意度：正面占比
    positive_count = db.query(func.count(Conversation.id)).filter(
        Conversation.sentiment == "正面"
    ).scalar() or 0
    sentiment_rate = round(positive_count / total_conversations * 100, 1) if total_conversations > 0 else 0

    # 平均延迟
    avg_latency = db.query(func.avg(Conversation.latency_ms)).filter(
        Conversation.latency_ms > 0
    ).scalar() or 0

    return {
        "total_sessions": total_sessions,
        "total_conversations": total_conversations,
        "sentiment_rate": sentiment_rate,
        "avg_latency_ms": round(avg_latency, 0),
    }


@router.get("/qa-hot")
def get_hot_qa(limit: int = Query(10, description="返回数量"), db: Session = Depends(get_db)):
    """获取热门问答 Top-N（按用户提问频次）"""
    hot = (
        db.query(Conversation.content, func.count(Conversation.id).label("count"))
        .filter(Conversation.role == "user")
        .group_by(Conversation.content)
        .order_by(func.count(Conversation.id).desc())
        .limit(limit)
        .all()
    )
    return [{"question": q[0], "count": q[1]} for q in hot]


@router.get("/sentiment")
def get_sentiment_trend(days: int = Query(7, description="统计天数"), db: Session = Depends(get_db)):
    """获取情感趋势（按天统计正面/中性/负面数量）"""
    since = datetime.utcnow() - timedelta(days=days)

    records = (
        db.query(
            func.date(Conversation.created_at).label("date"),
            Conversation.sentiment,
            func.count(Conversation.id).label("count"),
        )
        .filter(Conversation.created_at >= since, Conversation.sentiment != "")
        .group_by("date", Conversation.sentiment)
        .order_by("date")
        .all()
    )

    # 整理为按天的字典
    trend = {}
    for date_str, sentiment, count in records:
        ds = str(date_str)
        if ds not in trend:
            trend[ds] = {"date": ds, "正面": 0, "中性": 0, "负面": 0}
        trend[ds][sentiment] = count

    return list(trend.values())


@router.get("/daily")
def get_daily_stats(days: int = Query(7, description="统计天数"), db: Session = Depends(get_db)):
    """获取每日服务量"""
    since = datetime.utcnow() - timedelta(days=days)

    records = (
        db.query(
            func.date(Conversation.created_at).label("date"),
            func.count(Conversation.id).label("count"),
        )
        .filter(Conversation.created_at >= since)
        .group_by("date")
        .order_by("date")
        .all()
    )

    return [{"date": str(r[0]), "count": r[1]} for r in records]
