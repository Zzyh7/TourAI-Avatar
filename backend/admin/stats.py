"""
数据统计 API —— 大屏数据 / 热门问答 / 情感趋势 / 满意度 / 答不上率 / 负面对话记录。
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from database import get_db
from models.schema import Conversation, Session as SessionModel
from config import CONFIG

router = APIRouter(prefix="/api/admin/stats", tags=["数据统计"])


# ==================== 满意度计算（基于情感分析） ====================

def _calc_satisfaction(db: Session, since=None):
    """
    满意度 = (正面 + 中性) / (所有有情感标记的用户消息) × 100%
    中性视为满意侧（用户没表达不满即为满意）。
    同时返回显式满意度关键词统计。
    """
    base_q = db.query(Conversation).filter(
        Conversation.role == "user",
        Conversation.sentiment != "",
    )
    if since is not None:
        base_q = base_q.filter(Conversation.created_at >= since)

    total = base_q.count() or 1  # avoid div by zero
    positive = base_q.filter(Conversation.sentiment == "正面").count()
    neutral = base_q.filter(Conversation.sentiment == "中性").count()
    negative = base_q.filter(Conversation.sentiment == "负面").count()

    satisfied_side = positive + neutral
    rate = round(satisfied_side / total * 100, 1)

    # 显式满意度关键词
    explicit_s = db.query(Conversation).filter(
        Conversation.role == "user",
        Conversation.satisfaction == "satisfied",
    )
    explicit_u = db.query(Conversation).filter(
        Conversation.role == "user",
        Conversation.satisfaction == "unsatisfied",
    )
    if since is not None:
        explicit_s = explicit_s.filter(Conversation.created_at >= since)
        explicit_u = explicit_u.filter(Conversation.created_at >= since)

    return {
        "total_messages_with_sentiment": total,
        "positive": positive,
        "neutral": neutral,
        "negative": negative,
        "satisfaction_rate": rate,  # (正面+中性) / 总数
        "explicit_satisfied": explicit_s.count(),
        "explicit_unsatisfied": explicit_u.count(),
    }


def _calc_unanswered(db: Session, since=None):
    """答不上率 = is_unanswered==1 的助手消息 / 全部助手消息"""
    base = db.query(Conversation).filter(Conversation.role == "assistant")
    if since is not None:
        base = base.filter(Conversation.created_at >= since)
    total = base.count() or 1
    unanswered = base.filter(Conversation.is_unanswered == 1).count()
    return {
        "total_assistant_messages": total,
        "unanswered_count": unanswered,
        "unanswered_rate": round(unanswered / total * 100, 1),
    }


# ==================== 1. 总览 ====================

@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    """总览：服务人次、满意度（含中性）、答不上率、平均延迟"""
    total_sessions = db.query(func.count(SessionModel.id)).scalar() or 0
    total_conversations = db.query(func.count(Conversation.id)).scalar() or 0
    avg_latency = db.query(func.avg(Conversation.latency_ms)).filter(
        Conversation.latency_ms > 0
    ).scalar() or 0

    sat = _calc_satisfaction(db)
    una = _calc_unanswered(db)

    return {
        "total_sessions": total_sessions,
        "total_conversations": total_conversations,
        "satisfaction": sat,
        "unanswered": una,
        "avg_latency_ms": round(avg_latency, 0),
    }


# ==================== 2. 热门问答 ====================

@router.get("/qa-hot")
def get_hot_qa(limit: int = Query(10, description="返回数量"), db: Session = Depends(get_db)):
    """热门问答 Top-N"""
    hot = (
        db.query(Conversation.content, func.count(Conversation.id).label("count"))
        .filter(Conversation.role == "user")
        .group_by(Conversation.content)
        .order_by(func.count(Conversation.id).desc())
        .limit(limit)
        .all()
    )
    return [{"question": q[0], "count": q[1]} for q in hot]


# ==================== 3. 情感趋势 ====================

@router.get("/sentiment")
def get_sentiment_trend(days: int = Query(7, description="统计天数"), db: Session = Depends(get_db)):
    """按天统计正面/中性/负面数量"""
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
    trend = {}
    for date_str, sentiment, count in records:
        ds = str(date_str)
        if ds not in trend:
            trend[ds] = {"date": ds, "正面": 0, "中性": 0, "负面": 0}
        trend[ds][sentiment] = count
    return list(trend.values())


# ==================== 4. 每日服务量 ====================

@router.get("/daily")
def get_daily_stats(days: int = Query(7, description="统计天数"), db: Session = Depends(get_db)):
    """每日服务量"""
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


# ==================== 5. 数据大屏 ====================

@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    """数据大屏概览"""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)

    # 当日
    today_sessions = db.query(func.count(SessionModel.id)).filter(
        SessionModel.created_at >= today_start
    ).scalar() or 0
    today_convs = db.query(func.count(Conversation.id)).filter(
        Conversation.created_at >= today_start
    ).scalar() or 0

    # 本周
    week_sessions = db.query(func.count(SessionModel.id)).filter(
        SessionModel.created_at >= week_start
    ).scalar() or 0
    week_convs = db.query(func.count(Conversation.id)).filter(
        Conversation.created_at >= week_start
    ).scalar() or 0

    # 总览
    total_sessions = db.query(func.count(SessionModel.id)).scalar() or 0
    total_convs = db.query(func.count(Conversation.id)).scalar() or 0

    # 满意度 & 答不上（全局）
    sat = _calc_satisfaction(db)
    una = _calc_unanswered(db)

    # 本周每日趋势
    week_days = []
    for i in range(7):
        day = datetime.utcnow().date() - timedelta(days=6 - i)
        ds = datetime(day.year, day.month, day.day)
        de = ds + timedelta(days=1)
        count = db.query(func.count(Conversation.id)).filter(
            Conversation.created_at >= ds, Conversation.created_at < de,
        ).scalar() or 0
        pos = db.query(func.count(Conversation.id)).filter(
            Conversation.created_at >= ds, Conversation.created_at < de,
            Conversation.sentiment == "正面"
        ).scalar() or 0
        neg = db.query(func.count(Conversation.id)).filter(
            Conversation.created_at >= ds, Conversation.created_at < de,
            Conversation.sentiment == "负面"
        ).scalar() or 0
        unans = db.query(func.count(Conversation.id)).filter(
            Conversation.created_at >= ds, Conversation.created_at < de,
            Conversation.is_unanswered == 1,
        ).scalar() or 0
        week_days.append({
            "date": str(day), "total": count,
            "positive": pos, "negative": neg, "unanswered": unans,
        })

    # 热门提问
    hot_qa = (
        db.query(Conversation.content, func.count(Conversation.id).label("count"))
        .filter(Conversation.role == "user")
        .group_by(Conversation.content)
        .order_by(func.count(Conversation.id).desc())
        .limit(8)
        .all()
    )

    # 情感分布
    pos_all = db.query(func.count(Conversation.id)).filter(Conversation.sentiment == "正面").scalar() or 0
    neu_all = db.query(func.count(Conversation.id)).filter(Conversation.sentiment == "中性").scalar() or 0
    neg_all = db.query(func.count(Conversation.id)).filter(Conversation.sentiment == "负面").scalar() or 0

    return {
        "today": {"sessions": today_sessions, "conversations": today_convs},
        "week": {"sessions": week_sessions, "conversations": week_convs, "daily": week_days},
        "total": {"sessions": total_sessions, "conversations": total_convs},
        "satisfaction": sat,
        "unanswered": una,
        "sentiment_distribution": {"positive": pos_all, "neutral": neu_all, "negative": neg_all},
        "hot_questions": [{"question": q[0], "count": q[1]} for q in hot_qa],
    }


# ==================== 6. 负面对话记录 ====================

@router.get("/negative-conversations")
def get_negative_conversations(
    days: int = Query(7, description="统计天数"),
    page: int = Query(1, description="页码"),
    page_size: int = Query(20, description="每页数量"),
    db: Session = Depends(get_db),
):
    """
    负面对话记录：查询情感为负面 或 用户明确表示不满的对话。
    返回完整的问答对（用户消息 + AI回复），支持分页。
    """
    since = datetime.utcnow() - timedelta(days=days)

    # 找出负面情感的 session_id
    negative_sessions = (
        db.query(Conversation.session_id)
        .filter(
            Conversation.created_at >= since,
            Conversation.role == "user",
            or_(
                Conversation.sentiment == "负面",
                Conversation.satisfaction == "unsatisfied",
            ),
        )
        .distinct()
        .subquery()
    )

    # 获取这些 session 中的所有对话（按时间排序）
    total = (
        db.query(func.count(Conversation.id))
        .filter(Conversation.session_id.in_(negative_sessions))
        .scalar() or 0
    )

    records = (
        db.query(Conversation)
        .filter(Conversation.session_id.in_(negative_sessions))
        .order_by(Conversation.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # 按 session 分组整理
    from collections import defaultdict
    sessions_map = defaultdict(lambda: {"session_id": "", "user_msg": "", "ai_msg": "",
                                          "sentiment": "", "satisfaction": "", "time": "",
                                          "is_unanswered": False})
    for r in records:
        sid = r.session_id
        entry = sessions_map[sid]
        entry["session_id"] = sid
        entry["time"] = str(r.created_at) if entry["time"] == "" else entry["time"]
        if r.role == "user":
            entry["user_msg"] = r.content
            entry["sentiment"] = r.sentiment
            entry["satisfaction"] = r.satisfaction
        else:
            entry["ai_msg"] = r.content
            entry["is_unanswered"] = r.is_unanswered == 1

    items = list(sessions_map.values())
    items.sort(key=lambda x: x["time"], reverse=True)

    return {
        "period": f"近{days}天",
        "total_negative_sessions": len(items),
        "total_records": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


# ==================== 7. 游客感受度报告 ====================

@router.get("/report")
async def get_report(days: int = Query(7, description="统计天数"), db: Session = Depends(get_db)):
    """游客感受度报告：满意度 + 答不上率 + 关注点分析 + AI 建议"""
    since = datetime.utcnow() - timedelta(days=days)

    sat = _calc_satisfaction(db, since)
    una = _calc_unanswered(db, since)

    # 负面用户消息
    negative_msgs = (
        db.query(Conversation.content)
        .filter(
            Conversation.created_at >= since,
            Conversation.role == "user",
            or_(
                Conversation.sentiment == "负面",
                Conversation.satisfaction == "unsatisfied",
            ),
        )
        .limit(20)
        .all()
    )
    neg_texts = [m[0] for m in negative_msgs]

    # 热门提问
    hot_questions = (
        db.query(Conversation.content, func.count(Conversation.id).label("count"))
        .filter(Conversation.created_at >= since, Conversation.role == "user")
        .group_by(Conversation.content)
        .order_by(func.count(Conversation.id).desc())
        .limit(15)
        .all()
    )

    # 每日趋势
    daily_trend = []
    for i in range(days):
        day = datetime.utcnow().date() - timedelta(days=days - 1 - i)
        ds = datetime(day.year, day.month, day.day)
        de = ds + timedelta(days=1)
        dc = db.query(func.count(Conversation.id)).filter(
            Conversation.created_at >= ds, Conversation.created_at < de
        ).scalar() or 0
        dp = db.query(func.count(Conversation.id)).filter(
            Conversation.created_at >= ds, Conversation.created_at < de,
            Conversation.sentiment == "正面"
        ).scalar() or 0
        dn = db.query(func.count(Conversation.id)).filter(
            Conversation.created_at >= ds, Conversation.created_at < de,
            Conversation.sentiment == "负面"
        ).scalar() or 0
        du = db.query(func.count(Conversation.id)).filter(
            Conversation.created_at >= ds, Conversation.created_at < de,
            Conversation.is_unanswered == 1,
        ).scalar() or 0
        daily_trend.append({"date": str(day), "total": dc, "positive": dp, "negative": dn, "unanswered": du})

    # 关注点
    concern_keywords = {
        "灵山大佛": ["大佛", "灵山"], "九龙灌浴": ["九龙", "灌浴", "演出"],
        "梵宫": ["梵宫", "吉祥颂"], "五印坛城": ["五印", "坛城"],
        "拈花湾": ["拈花", "湾"], "门票价格": ["门票", "价格", "多少钱"],
        "开放时间": ["开门", "关门", "时间", "几点"], "交通出行": ["怎么去", "交通", "停车"],
        "餐饮住宿": ["吃", "住", "酒店", "素斋"], "游览路线": ["路线", "怎么逛", "安排"],
    }
    concern_count: dict[str, int] = {}
    for q, count in hot_questions:
        matched = False
        for cat, kws in concern_keywords.items():
            if any(kw in q for kw in kws):
                concern_count[cat] = concern_count.get(cat, 0) + count
                matched = True
                break
        if not matched:
            concern_count["其他"] = concern_count.get("其他", 0) + count
    concerns = sorted(
        [{"name": k, "count": v} for k, v in concern_count.items()],
        key=lambda x: x["count"], reverse=True,
    )

    # LLM 分析
    analysis_text = ""
    try:
        llm = CONFIG.create_llm()
        neg_summary = "\n".join(neg_texts[:10]) if neg_texts else "无负面反馈"
        hot_summary = ", ".join([f"{q[0]}({q[1]}次)" for q in hot_questions[:10]])
        concerns_summary = ", ".join([f"{c['name']}({c['count']}次)" for c in concerns[:5]])
        prompt = (
            "你是景区管理顾问。请根据以下数据，用简洁的专业语言（200字以内）总结：\n"
            "1. 游客满意度概况\n2. 主要关注点\n3. 答不上问题和负面反馈分析\n4. 服务改进建议\n\n"
            f"统计周期：近{days}天\n"
            f"总对话数：{sat['total_messages_with_sentiment']}，正面{sat['positive']}条，"
            f"中性{sat['neutral']}条，负面{sat['negative']}条\n"
            f"满意度（含中性）：{sat['satisfaction_rate']}%\n"
            f"答不上率：{una['unanswered_rate']}%（{una['unanswered_count']}次）\n"
            f"游客关注热点：{hot_summary}\n"
            f"关注分类：{concerns_summary}\n"
            f"负面反馈示例：{neg_summary}\n\n"
            "请用纯文本回复，不要使用任何markdown格式。"
        )
        response = await llm.ainvoke(prompt)
        analysis_text = response.content.strip()
        analysis_text = analysis_text.replace("*", "").replace("#", "")
    except Exception as e:
        analysis_text = f"（AI分析暂不可用：{e}）"

    return {
        "period": f"近{days}天",
        "summary": {
            **sat,
            **una,
        },
        "daily_trend": daily_trend,
        "concerns": concerns,
        "negative_samples": [{"content": t, "sentiment": "负面"} for t in neg_texts[:10]],
        "hot_questions": [{"question": q[0], "count": q[1]} for q in hot_questions],
        "ai_analysis": analysis_text,
    }
