"""
游客分析完整模块 —— 交互指标/景点热度/服务质量/时间对比/高频提问/游客分层/情感分析/导出
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, case, extract
from sqlalchemy.orm import Session
from collections import defaultdict

from database import get_db
from models.schema import Conversation, Session as SessionModel, ScenicSpot
from config import CONFIG

router = APIRouter(prefix="/api/admin/analytics", tags=["游客分析"])


# ========== 工具函数 ==========
def _day_range(days_ago=0):
    """返回某天的起止时间"""
    d = datetime.utcnow().date() - timedelta(days=days_ago)
    return datetime(d.year, d.month, d.day), datetime(d.year, d.month, d.day) + timedelta(days=1)

def _week_range():
    d = datetime.utcnow().date()
    start = d - timedelta(days=d.weekday())
    return datetime(start.year, start.month, start.day), datetime.utcnow()

def _month_range():
    d = datetime.utcnow().date()
    return datetime(d.year, d.month, 1), datetime.utcnow()


# ========== 1. 交互总量指标 ==========
@router.get("/interaction-metrics")
def interaction_metrics(db: Session = Depends(get_db)):
    """基础交互总量指标"""
    now = datetime.utcnow()
    today_s, today_e = _day_range(0)
    yesterday_s, yesterday_e = _day_range(1)
    week_s, week_e = _week_range()
    month_s, month_e = _month_range()

    # 人次统计
    def count_sessions(since, until):
        return db.query(func.count(SessionModel.id)).filter(
            SessionModel.created_at >= since, SessionModel.created_at < until
        ).scalar() or 0

    def count_convs(since, until):
        return db.query(func.count(Conversation.id)).filter(
            Conversation.created_at >= since, Conversation.created_at < until
        ).scalar() or 0

    # 新增游客（首次出现的session_id）
    def new_visitors(since, until):
        prior = db.query(func.count(SessionModel.id)).filter(
            SessionModel.created_at < since
        ).scalar() or 0
        return max(0, count_sessions(since, until))  # 简化：本时段新建session视为新游客

    # 回访游客（本时段内多于1条对话的session）
    repeat = db.query(func.count(func.distinct(Conversation.session_id))).filter(
        Conversation.created_at >= week_s
    ).scalar() or 0
    repeat_sessions = db.query(
        Conversation.session_id,
        func.count(Conversation.id).label("cnt")
    ).filter(
        Conversation.created_at >= week_s
    ).group_by(Conversation.session_id).having(func.count(Conversation.id) > 2).count()

    # 各时段交互高峰
    hourly = []
    for h in range(24):
        cnt = db.query(func.count(Conversation.id)).filter(
            extract('hour', Conversation.created_at) == h,
            Conversation.created_at >= month_s
        ).scalar() or 0
        hourly.append({"hour": h, "count": cnt})

    # 平均单次对话数（每session平均convs）
    total_week_sessions = count_sessions(week_s, week_e)
    total_week_convs = count_convs(week_s, week_e)
    avg_convs_per_session = round(total_week_convs / total_week_sessions, 1) if total_week_sessions > 0 else 0
    avg_daily_convs = round(total_week_convs / 7, 1)

    return {
        "today": {"sessions": count_sessions(today_s, today_e), "conversations": count_convs(today_s, today_e)},
        "yesterday": {"sessions": count_sessions(yesterday_s, yesterday_e), "conversations": count_convs(yesterday_s, yesterday_e)},
        "week": {"sessions": count_sessions(week_s, week_e), "conversations": count_convs(week_s, week_e)},
        "month": {"sessions": count_sessions(month_s, month_e), "conversations": count_convs(month_s, month_e)},
        "hourly_distribution": hourly,
        "avg_conversations_per_session": avg_convs_per_session,
        "avg_daily_conversations": avg_daily_convs,
        "repeat_visitors_week": repeat_sessions,
    }


# ========== 2. 景点热度 ==========
@router.get("/spot-popularity")
def spot_popularity(db: Session = Depends(get_db)):
    """景区景点热度排行 —— 基于关键词匹配"""
    month_s, month_e = _month_range()
    convs = db.query(Conversation.content).filter(
        Conversation.created_at >= month_s,
        Conversation.role == "user"
    ).all()

    # 关键词→景点映射
    spot_keywords = {
        "灵山大佛": ["大佛", "灵山"],
        "九龙灌浴": ["九龙", "灌浴"],
        "梵宫": ["梵宫", "吉祥颂"],
        "五印坛城": ["五印", "坛城"],
        "拈花湾": ["拈花", "香月花街"],
        "天下第一掌": ["天下第一", "佛手"],
        "阿育王柱": ["阿育王"],
        "降魔浮雕": ["降魔", "浮雕"],
        "百子戏弥勒": ["百子"],
        "曼飞龙塔": ["曼飞龙", "白塔"],
        "灵山胜境牌坊": ["牌坊"],
    }

    spot_counts = defaultdict(int)
    for (content,) in convs:
        for spot, keywords in spot_keywords.items():
            if any(kw in (content or "") for kw in keywords):
                spot_counts[spot] += 1
                break

    ranking = sorted(
        [{"name": k, "count": v} for k, v in spot_counts.items()],
        key=lambda x: x["count"], reverse=True
    )

    return {
        "ranking": ranking,
        "top5": ranking[:5],
        "cold_spots": [s for s in ranking if s["count"] == 0],
        "total_queries": len(convs),
    }


# ========== 3. AI问答服务质量 ==========
@router.get("/qa-quality")
def qa_quality(db: Session = Depends(get_db)):
    """AI问答服务质量总览"""
    month_s, month_e = _month_range()
    total = db.query(func.count(Conversation.id)).filter(
        Conversation.created_at >= month_s
    ).scalar() or 0

    pos = db.query(func.count(Conversation.id)).filter(
        Conversation.created_at >= month_s, Conversation.sentiment == "正面"
    ).scalar() or 0
    neu = db.query(func.count(Conversation.id)).filter(
        Conversation.created_at >= month_s, Conversation.sentiment == "中性"
    ).scalar() or 0
    neg = db.query(func.count(Conversation.id)).filter(
        Conversation.created_at >= month_s, Conversation.sentiment == "负面"
    ).scalar() or 0

    # "答不上"统计：包含"抱歉"的assistant回复
    unable = db.query(func.count(Conversation.id)).filter(
        Conversation.created_at >= month_s,
        Conversation.role == "assistant",
        Conversation.content.contains("抱歉")
    ).scalar() or 0

    return {
        "total_answers": total // 2,  # 约一半是assistant回复
        "unable_to_answer": unable,
        "unable_rate": round(unable / (total // 2) * 100, 1) if total > 0 else 0,
        "sentiment": {"positive": pos, "neutral": neu, "negative": neg},
        "satisfaction_rate": round(pos / total * 100, 1) if total > 0 else 0,
    }


# ========== 4. 时间对比 ==========
@router.get("/time-comparison")
def time_comparison(db: Session = Depends(get_db)):
    """今日vs昨日、本周vs上周对比"""
    today_s, today_e = _day_range(0)
    yesterday_s, yesterday_e = _day_range(1)

    def day_stats(s, e):
        total = db.query(func.count(Conversation.id)).filter(
            Conversation.created_at >= s, Conversation.created_at < e
        ).scalar() or 0
        pos = db.query(func.count(Conversation.id)).filter(
            Conversation.created_at >= s, Conversation.created_at < e, Conversation.sentiment == "正面"
        ).scalar() or 0
        sessions = db.query(func.count(SessionModel.id)).filter(
            SessionModel.created_at >= s, SessionModel.created_at < e
        ).scalar() or 0
        return {"conversations": total, "positive": pos, "sessions": sessions,
                "rate": round(pos / total * 100, 1) if total > 0 else 0}

    # 本周每天趋势
    week_daily = []
    for i in range(7):
        s, e = _day_range(6 - i)
        week_daily.append(day_stats(s, e))
    week_daily.reverse()

    # 上周 vs 本周
    this_week_s = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
    last_week_s = this_week_s - timedelta(days=7)
    last_week_e = this_week_s

    tw_convs = db.query(func.count(Conversation.id)).filter(Conversation.created_at >= this_week_s).scalar() or 0
    lw_convs = db.query(func.count(Conversation.id)).filter(
        Conversation.created_at >= last_week_s, Conversation.created_at < last_week_e
    ).scalar() or 0

    return {
        "today": day_stats(today_s, today_e),
        "yesterday": day_stats(yesterday_s, yesterday_e),
        "week_daily": week_daily,
        "this_week_total": tw_convs,
        "last_week_total": lw_convs,
        "week_change": round((tw_convs - lw_convs) / lw_convs * 100, 1) if lw_convs > 0 else 0,
    }


# ========== 5. 高频提问分类 ==========
@router.get("/question-analysis")
def question_analysis(db: Session = Depends(get_db)):
    """高频提问分类 + 未识别问题汇总"""
    month_s, month_e = _month_range()
    convs = db.query(Conversation.content, Conversation.sentiment).filter(
        Conversation.created_at >= month_s, Conversation.role == "user"
    ).all()

    categories = {
        "门票价格": ["门票", "价格", "多少钱", "票", "优惠"],
        "交通停车": ["怎么去", "交通", "停车", "开车", "公交", "地铁"],
        "景点历史文化": ["历史", "文化", "典故", "传说", "故事"],
        "游玩路线": ["路线", "怎么逛", "安排", "先", "顺序"],
        "餐饮住宿": ["吃", "住", "酒店", "素斋", "餐厅", "民宿"],
        "演出时间": ["演出", "几点", "时间", "几点开始"],
        "设施服务": ["厕所", "卫生间", "wifi", "寄存", "轮椅", "充电"],
    }

    cat_counts = defaultdict(int)
    uncategorized = []
    all_questions = defaultdict(int)

    for content, sentiment in convs:
        if not content: continue
        all_questions[content] += 1
        matched = False
        for cat, kws in categories.items():
            if any(kw in content for kw in kws):
                cat_counts[cat] += 1
                matched = True
                break
        if not matched:
            uncategorized.append({"question": content, "count": 1})

    # 汇总未分类
    uniq_uncat = defaultdict(int)
    for u in uncategorized:
        uniq_uncat[u["question"]] += 1

    top_questions = sorted(all_questions.items(), key=lambda x: x[1], reverse=True)[:20]

    # 收集"答不上"的问题
    unable_qs = db.query(Conversation.content).filter(
        Conversation.created_at >= month_s,
        Conversation.role == "assistant",
        Conversation.content.contains("抱歉")
    ).all()

    return {
        "category_distribution": [{"category": k, "count": v} for k, v in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)],
        "top_questions": [{"question": q, "count": c} for q, c in top_questions],
        "unable_to_answer_count": len(unable_qs),
        "unable_questions": [q[0][:100] for q in unable_qs[:15]],
    }


# ========== 6. 游客分层 ==========
@router.get("/visitor-segmentation")
def visitor_segmentation(db: Session = Depends(get_db)):
    """游客基础属性标签与分层统计"""
    month_s, month_e = _month_range()

    # 按会话数分群
    session_conv_counts = db.query(
        Conversation.session_id,
        func.count(Conversation.id).label("cnt")
    ).filter(
        Conversation.created_at >= month_s
    ).group_by(Conversation.session_id).all()

    single_visit = sum(1 for _, c in session_conv_counts if c <= 2)
    multi_visit = sum(1 for _, c in session_conv_counts if 2 < c <= 10)
    heavy_visit = sum(1 for _, c in session_conv_counts if c > 10)
    total_visitors = len(session_conv_counts)

    # 标签分类（基于内容关键词）
    all_user_msgs = db.query(Conversation.content).filter(
        Conversation.created_at >= month_s, Conversation.role == "user"
    ).all()

    tag_keywords = {
        "亲子游客": ["孩子", "小孩", "宝宝", "亲子", "儿童", "小朋友"],
        "中老年观光": ["老人", "爸妈", "父母", "年纪大", "退休"],
        "青年自由行": ["一个人", "自由行", "背包", "徒步"],
        "摄影爱好者": ["拍照", "摄影", "相机", "打卡", "照片"],
        "文化研学": ["历史", "文化", "典故", "佛教", "学习"],
        "情侣出游": ["女朋友", "男朋友", "情侣", "约会", "浪漫"],
    }

    tag_counts = defaultdict(int)
    for (content,) in all_user_msgs:
        if not content: continue
        for tag, kws in tag_keywords.items():
            if any(kw in content for kw in kws):
                tag_counts[tag] += 1
                break

    # 游玩偏好
    pref_keywords = {
        "自然风光": ["风景", "山水", "湖", "花", "季节", "景色", "美"],
        "历史人文": ["历史", "文化", "佛教", "典故", "故事", "传说"],
        "亲子游乐": ["孩子", "小孩", "亲子", "玩", "乐园"],
        "文创打卡": ["拍照", "打卡", "网红", "文创", "纪念", "文艺"],
    }

    pref_counts = defaultdict(int)
    for (content,) in all_user_msgs:
        if not content: continue
        for pref, kws in pref_keywords.items():
            if any(kw in content for kw in kws):
                pref_counts[pref] += 1
                break

    return {
        "total_visitors": total_visitors,
        "segments": {
            "single_visit": single_visit,
            "multi_visit": multi_visit,
            "heavy_visit": heavy_visit,
        },
        "tags": [{"tag": k, "count": v} for k, v in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)],
        "preferences": [{"preference": k, "count": v} for k, v in sorted(pref_counts.items(), key=lambda x: x[1], reverse=True)],
    }


# ========== 7. 负面反馈归类 ==========
@router.get("/negative-analysis")
def negative_analysis(db: Session = Depends(get_db)):
    """负面反馈归类统计"""
    month_s, month_e = _month_range()

    neg_msgs = db.query(Conversation.content).filter(
        Conversation.created_at >= month_s,
        Conversation.role == "user",
        Conversation.sentiment == "负面"
    ).all()

    # 自动归类
    neg_categories = {
        "讲解内容不全": ["不知道", "没说到", "不全", "没说", "没有讲"],
        "路线规划不合理": ["路线", "走不动", "太远", "绕路"],
        "等待时间长": ["等", "排队", "慢", "久"],
        "设施咨询无答案": ["厕所", "wifi", "寄存", "充电", "轮椅"],
        "门票相关不满": ["门票", "贵", "票价", "不值"],
        "服务态度": ["服务", "态度", "差", "不好"],
    }

    neg_cat_counts = defaultdict(int)
    unclassified = 0

    for (content,) in neg_msgs:
        if not content:
            unclassified += 1
            continue
        matched = False
        for cat, kws in neg_categories.items():
            if any(kw in content for kw in kws):
                neg_cat_counts[cat] += 1
                matched = True
                break
        if not matched:
            unclassified += 1

    # LLM优化建议
    suggestion = ""
    try:
        llm = CONFIG.create_llm()
        top_neg = sorted(neg_cat_counts.items(), key=lambda x: x[1], reverse=True)
        prompt = (
            f"你是景区运营顾问。近30天负面反馈共{len(neg_msgs)}条，分类如下："
            + ", ".join([f"{k}:{v}条" for k, v in top_neg])
            + "。请用100字以内给出3条最优先的改进建议。纯文本，无markdown。"
        )
        suggestion = llm.invoke(prompt).content.strip().replace("*", "").replace("#", "")
    except Exception:
        suggestion = "建议根据负面反馈分类，优先补充高频缺失知识、优化服务响应速度。"

    return {
        "total_negative": len(neg_msgs),
        "categories": [{"category": k, "count": v} for k, v in sorted(neg_cat_counts.items(), key=lambda x: x[1], reverse=True)],
        "unclassified": unclassified,
        "samples": [m[0][:100] for m in neg_msgs[:10]],
        "ai_suggestion": suggestion,
    }


# ========== 8. 综合仪表盘（所有模块数据合并） ==========
@router.get("/full-dashboard")
def full_dashboard(db: Session = Depends(get_db)):
    """综合仪表盘 —— 一次请求获取所有模块核心数据"""
    return {
        "interaction": interaction_metrics(db),
        "spot_popularity": spot_popularity(db),
        "qa_quality": qa_quality(db),
        "time_comparison": time_comparison(db),
        "question_analysis": question_analysis(db),
        "visitor_segmentation": visitor_segmentation(db),
    }
