"""
数据统计 API —— 大屏数据 / 热门问答 / 情感趋势 / 游客感受度报告。
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models.schema import Conversation, Session as SessionModel
from config import CONFIG

router = APIRouter(prefix="/api/admin/stats", tags=["数据统计"])


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    """获取总览数据（服务人次、满意度、答不上率、平均延迟）"""
    total_sessions = db.query(func.count(SessionModel.id)).scalar() or 0
    total_conversations = db.query(func.count(Conversation.id)).scalar() or 0

    # 正面情感占比（LLM情感分析）
    positive_count = db.query(func.count(Conversation.id)).filter(
        Conversation.sentiment == "正面"
    ).scalar() or 0
    sentiment_rate = round(positive_count / total_conversations * 100, 1) if total_conversations > 0 else 0

    # 显式满意度：用户明确说"我很满意"的占比
    satisfied_count = db.query(func.count(Conversation.id)).filter(
        Conversation.satisfaction == "satisfied"
    ).scalar() or 0
    unsatisfied_count = db.query(func.count(Conversation.id)).filter(
        Conversation.satisfaction == "unsatisfied"
    ).scalar() or 0
    satisfaction_total = satisfied_count + unsatisfied_count
    satisfaction_rate = round(satisfied_count / satisfaction_total * 100, 1) if satisfaction_total > 0 else 0

    # 答不上率：系统未能回答的问题占比（按助手回复统计）
    unanswered_count = db.query(func.count(Conversation.id)).filter(
        Conversation.is_unanswered == 1
    ).scalar() or 0
    assistant_count = db.query(func.count(Conversation.id)).filter(
        Conversation.role == "assistant"
    ).scalar() or 0
    unanswered_rate = round(unanswered_count / assistant_count * 100, 1) if assistant_count > 0 else 0

    # 平均延迟
    avg_latency = db.query(func.avg(Conversation.latency_ms)).filter(
        Conversation.latency_ms > 0
    ).scalar() or 0

    return {
        "total_sessions": total_sessions,
        "total_conversations": total_conversations,
        "sentiment_rate": sentiment_rate,
        "satisfaction_rate": satisfaction_rate,
        "satisfied_count": satisfied_count,
        "unsatisfied_count": unsatisfied_count,
        "unanswered_rate": unanswered_rate,
        "unanswered_count": unanswered_count,
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


# ==================== 数据大屏概览 ====================

@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    """
    数据大屏概览：当日/本周服务人次、热门问答、满意度趋势等核心运营数据。
    """
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    # 当日统计
    today_sessions = db.query(func.count(SessionModel.id)).filter(
        SessionModel.created_at >= today_start
    ).scalar() or 0

    today_convs = db.query(func.count(Conversation.id)).filter(
        Conversation.created_at >= today_start
    ).scalar() or 0

    today_positive = db.query(func.count(Conversation.id)).filter(
        Conversation.created_at >= today_start,
        Conversation.sentiment == "正面"
    ).scalar() or 0

    # 本周统计
    week_sessions = db.query(func.count(SessionModel.id)).filter(
        SessionModel.created_at >= week_start
    ).scalar() or 0

    week_convs = db.query(func.count(Conversation.id)).filter(
        Conversation.created_at >= week_start
    ).scalar() or 0

    week_positive = db.query(func.count(Conversation.id)).filter(
        Conversation.created_at >= week_start,
        Conversation.sentiment == "正面"
    ).scalar() or 0

    # 总览
    total_sessions = db.query(func.count(SessionModel.id)).scalar() or 0
    total_convs = db.query(func.count(Conversation.id)).scalar() or 0
    total_assistant = db.query(func.count(Conversation.id)).filter(
        Conversation.role == "assistant"
    ).scalar() or 0
    total_positive = db.query(func.count(Conversation.id)).filter(
        Conversation.sentiment == "正面"
    ).scalar() or 0

    # 满意度统计
    total_satisfied = db.query(func.count(Conversation.id)).filter(
        Conversation.satisfaction == "satisfied"
    ).scalar() or 0
    total_unsatisfied = db.query(func.count(Conversation.id)).filter(
        Conversation.satisfaction == "unsatisfied"
    ).scalar() or 0

    # 答不上率
    total_unanswered = db.query(func.count(Conversation.id)).filter(
        Conversation.is_unanswered == 1
    ).scalar() or 0

    # 本周每日趋势
    week_days = []
    for i in range(7):
        day = datetime.utcnow().date() - timedelta(days=6-i)
        day_start = datetime(day.year, day.month, day.day)
        day_end = day_start + timedelta(days=1)
        count = db.query(func.count(Conversation.id)).filter(
            Conversation.created_at >= day_start,
            Conversation.created_at < day_end,
        ).scalar() or 0
        positive = db.query(func.count(Conversation.id)).filter(
            Conversation.created_at >= day_start,
            Conversation.created_at < day_end,
            Conversation.sentiment == "正面"
        ).scalar() or 0
        negative = db.query(func.count(Conversation.id)).filter(
            Conversation.created_at >= day_start,
            Conversation.created_at < day_end,
            Conversation.sentiment == "负面"
        ).scalar() or 0
        unanswered = db.query(func.count(Conversation.id)).filter(
            Conversation.created_at >= day_start,
            Conversation.created_at < day_end,
            Conversation.is_unanswered == 1,
        ).scalar() or 0
        week_days.append({
            "date": str(day),
            "total": count,
            "positive": positive,
            "negative": negative,
            "unanswered": unanswered,
        })

    # 热门提问 Top 8
    hot_qa = (
        db.query(Conversation.content, func.count(Conversation.id).label("count"))
        .filter(Conversation.role == "user")
        .group_by(Conversation.content)
        .order_by(func.count(Conversation.id).desc())
        .limit(8)
        .all()
    )

    # 情感分布
    pos_all = db.query(func.count(Conversation.id)).filter(
        Conversation.sentiment == "正面"
    ).scalar() or 0
    neu_all = db.query(func.count(Conversation.id)).filter(
        Conversation.sentiment == "中性"
    ).scalar() or 0
    neg_all = db.query(func.count(Conversation.id)).filter(
        Conversation.sentiment == "负面"
    ).scalar() or 0

    return {
        "today": {
            "sessions": today_sessions,
            "conversations": today_convs,
            "positive_rate": round(today_positive / today_convs * 100, 1) if today_convs > 0 else 0,
        },
        "week": {
            "sessions": week_sessions,
            "conversations": week_convs,
            "positive_rate": round(week_positive / week_convs * 100, 1) if week_convs > 0 else 0,
            "daily": week_days,
        },
        "total": {
            "sessions": total_sessions,
            "conversations": total_convs,
            "positive_rate": round(total_positive / total_convs * 100, 1) if total_convs > 0 else 0,
        },
        "satisfaction": {
            "satisfied": total_satisfied,
            "unsatisfied": total_unsatisfied,
            "rate": round(total_satisfied / (total_satisfied + total_unsatisfied) * 100, 1) if (total_satisfied + total_unsatisfied) > 0 else 0,
        },
        "unanswered": {
            "count": total_unanswered,
            "rate": round(total_unanswered / total_assistant * 100, 1) if total_assistant > 0 else 0,
        },
        "sentiment_distribution": {
            "positive": pos_all,
            "neutral": neu_all,
            "negative": neg_all,
        },
        "hot_questions": [{"question": q[0], "count": q[1]} for q in hot_qa],
    }


# ==================== 游客感受度报告 ====================

@router.get("/report")
async def get_report(days: int = Query(7, description="统计天数"), db: Session = Depends(get_db)):
    """
    游客感受度报告：分析交互记录，生成游客关注点分析、情感趋势及服务改进建议。
    调用 LLM 对关键数据进行分析总结。
    """
    since = datetime.utcnow() - timedelta(days=days)

    # 基础统计数据
    total = db.query(func.count(Conversation.id)).filter(
        Conversation.created_at >= since
    ).scalar() or 0

    pos_count = db.query(func.count(Conversation.id)).filter(
        Conversation.created_at >= since, Conversation.sentiment == "正面"
    ).scalar() or 0
    neu_count = db.query(func.count(Conversation.id)).filter(
        Conversation.created_at >= since, Conversation.sentiment == "中性"
    ).scalar() or 0
    neg_count = db.query(func.count(Conversation.id)).filter(
        Conversation.created_at >= since, Conversation.sentiment == "负面"
    ).scalar() or 0

    # 满意度统计
    satisfied_count = db.query(func.count(Conversation.id)).filter(
        Conversation.created_at >= since, Conversation.satisfaction == "satisfied"
    ).scalar() or 0
    unsatisfied_count = db.query(func.count(Conversation.id)).filter(
        Conversation.created_at >= since, Conversation.satisfaction == "unsatisfied"
    ).scalar() or 0

    # 答不上统计
    unanswered_count = db.query(func.count(Conversation.id)).filter(
        Conversation.created_at >= since, Conversation.is_unanswered == 1
    ).scalar() or 0
    assistant_total = db.query(func.count(Conversation.id)).filter(
        Conversation.created_at >= since, Conversation.role == "assistant"
    ).scalar() or 0

    # 负面用户消息（用于分析痛点）
    negative_msgs = (
        db.query(Conversation.content)
        .filter(
            Conversation.created_at >= since,
            Conversation.role == "user",
            Conversation.sentiment == "负面"
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

    # 关注点统计（从热门提问中提取关键词）
    concern_keywords = {}
    for q, count in hot_questions:
        # 简单关键词归类
        keywords = {
            "灵山大佛": ["大佛", "灵山"],
            "九龙灌浴": ["九龙", "灌浴", "演出"],
            "梵宫": ["梵宫", "吉祥颂"],
            "五印坛城": ["五印", "坛城"],
            "拈花湾": ["拈花", "湾"],
            "门票价格": ["门票", "价格", "多少钱"],
            "开放时间": ["开门", "关门", "时间", "几点"],
            "交通出行": ["怎么去", "交通", "停车"],
            "餐饮住宿": ["吃", "住", "酒店", "素斋"],
            "游览路线": ["路线", "怎么逛", "安排"],
        }
        matched = False
        for cat, kws in keywords.items():
            if any(kw in q for kw in kws):
                concern_keywords[cat] = concern_keywords.get(cat, 0) + count
                matched = True
                break
        if not matched:
            concern_keywords["其他"] = concern_keywords.get("其他", 0) + count

    # 按频次排序关注点
    concerns = sorted(
        [{"name": k, "count": v} for k, v in concern_keywords.items()],
        key=lambda x: x["count"], reverse=True
    )

    # 调用 LLM 生成分析报告
    analysis_text = ""
    try:
        llm = CONFIG.create_llm()
        neg_summary = "\n".join(neg_texts[:10]) if neg_texts else "无负面反馈"
        hot_summary = ", ".join([f"{q[0]}({q[1]}次)" for q in hot_questions[:10]])
        concerns_summary = ", ".join([f"{c['name']}({c['count']}次)" for c in concerns[:5]])

        prompt = (
            "你是景区管理顾问。请根据以下数据，用简洁的专业语言（200字以内）总结：\n"
            "1. 游客感受度概况\n2. 主要关注点\n3. 服务改进建议\n\n"
            f"统计周期：近{days}天\n"
            f"总对话数：{total}，正面{pos_count}条，中性{neu_count}条，负面{neg_count}条\n"
            f"满意度：{round(pos_count/total*100,1) if total>0 else 0}%\n"
            f"游客关注热点：{hot_summary}\n"
            f"关注分类：{concerns_summary}\n"
            f"负面反馈示例：{neg_summary}\n\n"
            "请用纯文本回复，不要使用任何markdown格式。"
        )
        response = await llm.ainvoke(prompt)
        analysis_text = response.content.strip()
        # Clean markdown
        analysis_text = analysis_text.replace("*", "").replace("#", "")
    except Exception as e:
        analysis_text = f"（AI分析暂不可用：{e}）"

    return {
        "period": f"近{days}天",
        "summary": {
            "total_conversations": total,
            "positive": pos_count,
            "neutral": neu_count,
            "negative": neg_count,
            "satisfaction_rate": round(pos_count / total * 100, 1) if total > 0 else 0,
            "explicit_satisfied": satisfied_count,
            "explicit_unsatisfied": unsatisfied_count,
            "unanswered_count": unanswered_count,
            "unanswered_rate": round(unanswered_count / assistant_total * 100, 1) if assistant_total > 0 else 0,
        },
        "daily_trend": daily_trend,
        "concerns": concerns,
        "negative_samples": [{"content": t, "sentiment": "负面"} for t in neg_texts[:10]],
        "hot_questions": [{"question": q[0], "count": q[1]} for q in hot_questions],
        "ai_analysis": analysis_text,
    }
