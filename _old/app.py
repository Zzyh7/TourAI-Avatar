"""智能旅行助手 — Streamlit Web 界面。"""
import asyncio
from datetime import date

import streamlit as st

# ---- 页面配置 ----
st.set_page_config(
    page_title="智能旅行助手",
    page_icon="🧳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- CSS 样式 ----
st.markdown("""
<style>
    .main-header {
        font-size: 2rem; font-weight: 700; padding: 0.5rem 0;
        border-bottom: 3px solid #4A90D9; margin-bottom: 1rem;
    }
    .plan-title {
        font-size: 1.4rem; font-weight: 700; color: #2E7D32;
        text-align: center; margin: 1rem 0;
    }
    .day-header {
        font-size: 1.1rem; font-weight: 700; color: #1565C0;
        border-bottom: 2px solid #BBDEFB; padding: 0.5rem 0; margin: 1rem 0 0.5rem;
    }
    .weather-card {
        background: #E3F2FD; border-radius: 10px; padding: 1rem; margin: 0.5rem 0;
        color: #1a1a1a;
    }
    .weather-card b {
        color: #1565C0;
    }
    .budget-card {
        background: #FFF8E1; border-radius: 10px; padding: 1rem; margin: 0.5rem 0;
        color: #1a1a1a;
    }
</style>
""", unsafe_allow_html=True)


# ---- 初始化 ----
@st.cache_resource
def get_planner():
    from config import CONFIG
    from agents.planner import TripPlanner
    llm = CONFIG.create_llm()
    return TripPlanner(llm)


# ---- 辅助: 构建 prompt ----
def build_prompt(
    city: str,
    start_date: date,
    end_date: date,
    transport: list[str],
    hotel_type: str,
    preferences: list[str],
    extra: str,
) -> str:
    days = (end_date - start_date).days
    parts = [
        f"{city}{days}日游",
        f"{start_date.strftime('%Y年%m月%d日')}-{end_date.strftime('%Y年%m月%d日')}",
    ]
    if preferences:
        parts.append(f"喜欢{'、'.join(preferences)}")
    if hotel_type:
        parts.append(f"住宿偏好{hotel_type}")
    if transport:
        parts.append(f"交通方式偏好{'、'.join(transport)}")
    if extra.strip():
        parts.append(f"额外要求: {extra.strip()}")
    parts.append("中等预算")
    return "，".join(parts)


# ---- 辅助: 转换流式事件 ----
_SILENCE_NAMES = {"maps_weather", "maps_text_search", "maps_search_detail",
                   "maps_direction_walking", "maps_direction_driving",
                   "maps_direction_transit_integrated", "maps_direction_bicycling",
                   "maps_distance", "maps_geo", "maps_regeocode",
                   "maps_ip_location", "maps_around_search",
                   "maps_schema_personal_map", "maps_schema_navi",
                   "maps_schema_take_taxi"}

_STREAM_LABELS = {
    "query_weather":     "🌤️ 查询天气中...",
    "search_hotel":      "🏨 搜索酒店中...",
    "search_attraction": "🏛️ 搜索景点中...",
    "maps_direction_walking_by_address":             "🚶 规划步行路线...",
    "maps_direction_driving_by_address":             "🚗 规划驾车路线...",
    "maps_direction_transit_integrated_by_address":  "🚌 规划公交路线...",
}

# ---- 主 UI ----
st.markdown('<div class="main-header">🧳 智能旅行助手</div>', unsafe_allow_html=True)

# ============ 侧边栏: 参数输入 ============
with st.sidebar:
    st.markdown("### 📋 旅行参数")

    city = st.text_input("📍 目的地城市", placeholder="例如: 杭州、成都、三亚...")

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("📅 开始日期", value=date.today())
    with col2:
        end_date = st.date_input("📅 结束日期", value=date.today())

    if start_date and end_date and end_date >= start_date:
        trip_days = (end_date - start_date).days
        st.info(f"📌 共计 **{trip_days}** 天")
    elif end_date < start_date:
        st.error("结束日期不能早于开始日期")

    st.markdown("---")
    st.markdown("### 🚗 交通方式")
    transport_options = ["公共交通", "自驾", "打车/网约车", "骑行", "步行"]
    transport_selected = []
    for opt in transport_options:
        if st.checkbox(opt, key=f"trans_{opt}"):
            transport_selected.append(opt)

    st.markdown("---")
    st.markdown("### 🏨 住宿偏好")
    hotel_type = st.selectbox(
        "住宿类型",
        ["不限", "经济型酒店", "中档型酒店", "豪华型酒店", "民宿/客栈", "青年旅舍"],
        index=2,
        label_visibility="collapsed",
    )
    if hotel_type == "不限":
        hotel_type = ""

    st.markdown("---")
    st.markdown("### 🎯 旅行偏好")
    pref_options = ["自然风光", "历史文化", "美食探店", "休闲度假", "艺术展览", "购物逛街", "亲子乐园"]
    pref_selected = []
    for opt in pref_options:
        if st.checkbox(opt, key=f"pref_{opt}"):
            pref_selected.append(opt)

    st.markdown("---")
    st.markdown("### 💬 额外要求")
    extra_requirements = st.text_area(
        "补充说明",
        placeholder="例如: 带老人出行需要轻松行程、想在市中心活动...",
        label_visibility="collapsed",
    )

    st.markdown("---")
    submit_btn = st.button("🚀 开始规划", type="primary", use_container_width=True)


# ============ 主区域: 结果展示 ============
if "plan_data" not in st.session_state:
    st.session_state.plan_data = None
if "plan_raw" not in st.session_state:
    st.session_state.plan_raw = ""

# 未开始时的引导页
if not submit_btn and st.session_state.plan_data is None:
    st.info("👈 在左侧填写旅行参数，然后点击 **开始规划** 按钮")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("##### 🌤️ 实时天气查询")
        st.caption("接入高德地图 MCP，获取目的地准确天气预报")
    with col_b:
        st.markdown("##### 🏛️ 智能景点推荐")
        st.caption("根据你的偏好，AI 精准匹配最适合的景点和路线")
    with col_c:
        st.markdown("##### 📊 预算自动汇总")
        st.caption("景点门票、餐饮、住宿、交通费用一目了然")

# 点击按钮后执行
if submit_btn:
    if not city.strip():
        st.error("请输入目的地城市")
    elif end_date < start_date:
        st.error("结束日期不能早于开始日期")
    else:
        planner = get_planner()
        prompt = build_prompt(
            city, start_date, end_date,
            transport_selected, hotel_type, pref_selected, extra_requirements,
        )

        # 流式输出区域
        with st.spinner("🤖 AI 正在为您规划旅行方案..."):
            from render import parse_plan

            stream_placeholder = st.empty()
            status_placeholder = st.empty()

            async def _collect():
                results = []
                async for token in planner.stream(prompt):
                    results.append(token)
                return results

            tokens = asyncio.run(_collect())

            # 分离状态行和内容
            full_text = ""
            status_lines = []
            for token in tokens:
                full_text += token
                stripped = token.strip()
                if any(stripped.startswith(emoji) for emoji in ["🌤️", "🏨", "🏛️", "🚶", "🚗", "🚌"]):
                    status_lines.append(stripped)

            # 显示状态
            if status_lines:
                status_placeholder.markdown(
                    "  \n".join(status_lines) + "  \n✅ 生成完成！"
                )

            # 解析并存储
            plan = parse_plan(full_text)
            st.session_state.plan_data = plan
            st.session_state.plan_raw = full_text
            st.session_state.status_lines = status_lines

        st.rerun()


# ============ 结果展示 ============
plan = st.session_state.plan_data
if plan is not None:
    # 显示状态
    if "status_lines" in st.session_state and st.session_state.status_lines:
        with st.expander("🔍 规划过程", expanded=False):
            st.markdown("\n".join(st.session_state.status_lines))

    # ---- 标题 ----
    city = plan.get("city", "")
    sd = plan.get("start_date", "")
    ed = plan.get("end_date", "")
    st.markdown(
        f'<div class="plan-title">🌴 {city}旅行计划 ｜ {sd} ~ {ed}</div>',
        unsafe_allow_html=True,
    )

    # ---- 天气卡片 ----
    weather = plan.get("weather_info", [])
    if weather:
        st.markdown("##### 🌤️ 天气预报")
        cols = st.columns(len(weather))
        weather_icon_map = {
            "晴": "☀️", "多云": "⛅", "阴": "☁️",
            "小雨": "🌧️", "中雨": "🌧️", "大雨": "⛈️", "暴雨": "⛈️",
        }

        for i, w in enumerate(weather):
            d = w.get("date", "")[-5:]
            di = weather_icon_map.get(w.get("day_weather", ""), "🌡️")
            with cols[i]:
                st.markdown(
                    f"""<div class="weather-card" style="text-align:center">
                    <b>{d}</b><br>
                    {di} {w.get('day_weather', '?')}<br>
                    🌡️ {w.get('day_temp', '?')}°C / {w.get('night_temp', '?')}°C<br>
                    💨 {w.get('wind_direction', '')}{w.get('wind_power', '')}
                    </div>""",
                    unsafe_allow_html=True,
                )

    # ---- 每日行程 ----
    st.markdown("---")
    st.markdown("##### 📅 每日行程")

    days = plan.get("days", [])
    if days:
        tabs = st.tabs([f"Day {d.get('day_index', i) + 1}" for i, d in enumerate(days)])
        for i, (tab, day) in enumerate(zip(tabs, days)):
            with tab:
                d = day.get("date", "")[-5:]
                desc = day.get("description", "")

                st.markdown(f'<div class="day-header">📅 {d}  {desc}</div>', unsafe_allow_html=True)

                # 住宿
                hotel = day.get("hotel", {})
                if hotel.get("name"):
                    st.markdown(
                        f"🏨 **{hotel['name']}**  ★{hotel.get('rating', '-')}  "
                        f"¥{hotel.get('estimated_cost', 0)}/晚  |  {hotel.get('address', '')}"
                    )
                st.caption(f"🚌 {day.get('transportation', '')}")

                # 景点
                attractions = day.get("attractions", [])
                if attractions:
                    st.markdown("**🏛️ 景点**")
                    for a in attractions:
                        ticket = a.get("ticket_price", 0)
                        ts = "🆓 免费" if ticket == 0 else f"🎫 ¥{ticket}"
                        with st.container(border=True):
                            st.markdown(
                                f"**{a.get('name', '?')}**  |  {a.get('category', '')}  |  "
                                f"⏱️ {a.get('visit_duration', 0)}分钟  |  {ts}"
                            )
                            st.caption(a.get("address", ""))
                            if a.get("description"):
                                st.caption(a["description"])

                # 餐饮
                meals = day.get("meals", [])
                if meals:
                    st.markdown("**🍽️ 餐饮推荐**")
                    mt = {"breakfast": "🌅 早餐", "lunch": "☀️ 午餐", "dinner": "🌙 晚餐"}
                    meal_cols = st.columns(len(meals))
                    for j, m in enumerate(meals):
                        label = mt.get(m.get("type", ""), "餐")
                        with meal_cols[j]:
                            st.markdown(
                                f"*{label}*\n\n**{m.get('name', '?')}**  \n"
                                f"¥{m.get('estimated_cost', 0)}"
                            )

    # ---- 预算 ----
    budget = plan.get("budget", {})
    if budget:
        st.markdown("---")
        st.markdown("##### 💰 预算汇总")
        bc1, bc2, bc3, bc4, bc5 = st.columns(5)
        with bc1:
            st.metric("景点门票", f"¥{budget.get('total_attractions', 0):,}")
        with bc2:
            st.metric("酒店住宿", f"¥{budget.get('total_hotels', 0):,}")
        with bc3:
            st.metric("餐饮美食", f"¥{budget.get('total_meals', 0):,}")
        with bc4:
            st.metric("交通出行", f"¥{budget.get('total_transportation', 0):,}")
        with bc5:
            st.metric("📊 总计", f"¥{budget.get('total', 0):,}",
                      delta=None, delta_color="off")

    # ---- 建议 ----
    suggestions = plan.get("overall_suggestions", "")
    if suggestions:
        st.markdown("---")
        st.markdown("##### 💡 旅行建议")
        for tip in suggestions.replace("；", ";").split(";"):
            tip = tip.strip()
            if tip:
                st.markdown(f"- {tip}")

    # ============ 导出 ============
    st.markdown("---")
    st.markdown("##### 📥 导出计划")

    def _build_markdown(p):
        md = f"# 🌴 {p.get('city', '')}旅行计划\n\n"
        md += f"**日期:** {p.get('start_date', '')} ~ {p.get('end_date', '')}\n\n"

        md += "## 🌤️ 天气预报\n\n"
        for w in p.get("weather_info", []):
            md += (
                f"- {w.get('date', '')[-5:]}: "
                f"{w.get('day_weather', '')}/{w.get('night_weather', '')}  "
                f"{w.get('day_temp', '')}°C~{w.get('night_temp', '')}°C  "
                f"{w.get('wind_direction', '')}{w.get('wind_power', '')}\n"
            )

        md += "\n## 📅 每日行程\n\n"
        for day in p.get("days", []):
            idx = day.get("day_index", 0) + 1
            md += f"### Day {idx} — {day.get('date', '')[-5:]}  {day.get('description', '')}\n\n"
            h = day.get("hotel", {})
            if h.get("name"):
                md += f"- **住宿:** {h['name']}  ★{h.get('rating', '')}  ¥{h.get('estimated_cost', 0)}/晚  |  {h.get('address', '')}\n"
            md += f"- **交通:** {day.get('transportation', '')}\n"
            for a in day.get("attractions", []):
                t = "免费" if a.get("ticket_price", 0) == 0 else f"¥{a.get('ticket_price', 0)}"
                md += f"  - **{a.get('name', '')}** ({a.get('category', '')})  ⏱️{a.get('visit_duration', 0)}分钟  {t}  |  {a.get('address', '')}\n"
            for m in day.get("meals", []):
                mt = {"breakfast": "早餐", "lunch": "午餐", "dinner": "晚餐"}
                md += f"  - {mt.get(m.get('type', ''), '餐')}: {m.get('name', '')}  ¥{m.get('estimated_cost', 0)}\n"
            md += "\n"

        b = p.get("budget", {})
        if b:
            md += "## 💰 预算汇总\n\n"
            md += f"| 项目 | 金额 |\n|------|------|\n"
            md += f"| 景点门票 | ¥{b.get('total_attractions', 0):,} |\n"
            md += f"| 酒店住宿 | ¥{b.get('total_hotels', 0):,} |\n"
            md += f"| 餐饮美食 | ¥{b.get('total_meals', 0):,} |\n"
            md += f"| 交通出行 | ¥{b.get('total_transportation', 0):,} |\n"
            md += f"| **总计** | **¥{b.get('total', 0):,}** |\n"

        sug = p.get("overall_suggestions", "")
        if sug:
            md += "\n## 💡 旅行建议\n\n"
            for tip in sug.replace("；", ";").split(";"):
                tip = tip.strip()
                if tip:
                    md += f"- {tip}\n"
        return md

    md_content = _build_markdown(plan)
    st.download_button(
        label="📄 下载 Markdown",
        data=md_content,
        file_name=f"{plan.get('city', '旅行')}_旅行计划.md",
        mime="text/markdown",
        use_container_width=True,
    )
