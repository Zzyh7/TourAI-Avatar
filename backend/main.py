"""
景区导览AI数字人 — FastAPI 统一入口。

多模态支持:
  - 文本问答: RAG 检索 (FAISS+BM25+RRF) + DeepSeek 生成
  - 拍照识景: 通义千问-VL 识别 + RAG 知识库增强
  - 语音输入: 前端 Web Speech API → 文本 → 后端处理

启动:
    cd backend
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""
import os
import time
import uuid
import json
import asyncio
from typing import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from config import CONFIG
from database import init_db, get_db
from models.schema import ScenicSpot, Session as SessionModel
from agents.planner import GuideAgent
from services.tts.edge_tts import tts_service
from admin.knowledge import router as knowledge_router
from admin.config_router import router as config_router
from admin.stats import router as stats_router
from rag_system import rag_router, init_rag, get_retriever


# ==================== 全局服务实例 ====================
guide_agent: GuideAgent | None = None


# ==================== 生命周期 ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化所有服务"""
    global guide_agent

    print("[START] 景区导览AI数字人 启动中...")

    # 1. 初始化数据库（可选，失败不阻塞）
    try:
        init_db()
        print("[OK] 数据库就绪")
    except Exception as e:
        print(f"[WARN] 数据库初始化失败 (不影响核心功能): {e}")

    # 2. 初始化 RAG 知识库 (FAISS + BM25 + SQLite)
    init_rag()
    print("[OK] RAG 知识库就绪")

    # 3. 尝试初始化 GuideAgent (DeepSeek + MCP + RAG)
    # 设置 SKIP_MCP=1 环境变量可跳过 MCP 连接（测试时启动更快）
    skip_mcp = os.environ.get("SKIP_MCP", "0") == "1"
    llm = CONFIG.create_llm()
    guide_agent = GuideAgent(llm, get_retriever())

    if skip_mcp:
        print("[INFO] SKIP_MCP=1, 跳过 MCP 连接, 使用纯 RAG + LLM 模式")
        guide_agent = None
    else:
        try:
            # MCP 连接高德地图，设置 10 秒超时避免卡启动
            await asyncio.wait_for(guide_agent.build(), timeout=10.0)
            print("[OK] GuideAgent 就绪 (Agent + MCP + RAG)")
        except asyncio.TimeoutError:
            print("[WARN] MCP 连接超时 (10s), 降级为纯 RAG + LLM")
            guide_agent = None
        except Exception as e:
            print(f"[WARN] MCP 不可用, 降级为纯 RAG + LLM: {e}")
            guide_agent = None

    print("[READY] 服务启动完成")
    yield
    print("[STOP] 服务关闭")


# ==================== FastAPI App ====================

app = FastAPI(
    title="景区导览AI数字人",
    description="A5竞赛项目 — 智能景区导览数字人后端服务 (多模态)",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — 允许前端跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册管理后台路由
app.include_router(knowledge_router)
app.include_router(config_router)
app.include_router(stats_router)

# 注册 RAG 增强知识库路由 (独立 /api/rag/query + /api/rag/admin/upload/faq)
app.include_router(rag_router, prefix="/api/rag")


# ==================== 请求/响应模型 ====================

class ChatRequest(BaseModel):
    text: str
    session_id: str = ""


class PhotoRequest(BaseModel):
    image: str               # base64 编码的图片
    lat: float | None = None
    lng: float | None = None


class SessionTagRequest(BaseModel):
    """会话标签更新"""
    tag: str = ""            # 家庭游/情侣游/文化深度游/休闲游


# ==================== 游客端 API ====================

@app.post("/api/session/new")
def create_session(db: Session = Depends(get_db)):
    """创建新会话，返回 session_id"""
    session = SessionModel(
        id=uuid.uuid4().hex[:12],
        visitor_tag="",
    )
    db.add(session)
    db.commit()
    return {"session_id": session.id}


@app.put("/api/session/{session_id}/tag")
def update_session_tag(session_id: str, data: SessionTagRequest, db: Session = Depends(get_db)):
    """更新会话的游客标签"""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if session:
        session.visitor_tag = data.tag
        db.commit()
    return {"session_id": session_id, "tag": data.tag}


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    文本问答 + TTS 语音合成（SSE 流式）—— 支持语音+文本混合输入。

    前端通过 Web Speech API 将语音转为文本后调用此端点。
    后端使用 RAG 检索 + DeepSeek 生成回答，并通过 Edge-TTS 合成语音。

    返回 SSE 事件流:
      event: token  → 文本 token
      event: audio  → TTS 音频片段 (base64 mp3)
      event: tool   → 工具调用状态 (仅 Agent 模式)
      event: done   → 完成标记
    """
    session_id = request.session_id or uuid.uuid4().hex[:12]
    start_time = time.time()

    async def event_generator() -> AsyncIterator[str]:
        full_answer = ""
        sentence_buffer = ""

        try:
            if guide_agent is not None:
                # === Agent 模式: GuideAgent (MCP工具 + RAG) ===
                async for event in guide_agent.stream(request.text, session_id):
                    if event["type"] == "token":
                        token = event["data"]
                        full_answer += token
                        sentence_buffer += token
                        yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"
                        if any(punct in token for punct in "。！？\n"):
                            if sentence_buffer.strip():
                                audio_b64 = await tts_service.synthesize(sentence_buffer)
                                if audio_b64:
                                    yield f"event: audio\ndata: {json.dumps({'base64': audio_b64, 'text': sentence_buffer.strip()})}\n\n"
                            sentence_buffer = ""
                    elif event["type"] == "tool_start":
                        yield f"event: tool\ndata: {json.dumps({'status': 'start', 'label': event['data']['label']})}\n\n"
                    elif event["type"] == "done":
                        if sentence_buffer.strip():
                            audio_b64 = await tts_service.synthesize(sentence_buffer)
                            if audio_b64:
                                yield f"event: audio\ndata: {json.dumps({'base64': audio_b64, 'text': sentence_buffer.strip()})}\n\n"
                        break
            else:
                # === Direct RAG + LLM 模式 ===
                retriever = get_retriever()
                rag_result = retriever.retrieve(request.text, top_k=5)
                context = "\n---\n".join(
                    doc.page_content for doc in rag_result.get("docs", [])
                ) if rag_result.get("docs") else "暂无相关资料"

                llm = CONFIG.create_llm()
                prompt = (
                    "你是一个专业的景区导览数字人，名叫小导。请基于【参考资料】回答问题。\n"
                    "如果参考资料不足以回答，请直接说「资料中没有相关信息」，不要编造。\n\n"
                    f"【用户问题】：{request.text}\n\n"
                    f"【参考资料】：\n{context}"
                )
                # 流式输出 token
                async for chunk in llm.astream(prompt):
                    token = chunk.content if hasattr(chunk, 'content') else str(chunk)
                    if token:
                        full_answer += token
                        sentence_buffer += token
                        yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"
                        if any(punct in token for punct in "。！？\n"):
                            if sentence_buffer.strip():
                                audio_b64 = await tts_service.synthesize(sentence_buffer)
                                if audio_b64:
                                    yield f"event: audio\ndata: {json.dumps({'base64': audio_b64, 'text': sentence_buffer.strip()})}\n\n"
                            sentence_buffer = ""

                if sentence_buffer.strip():
                    audio_b64 = await tts_service.synthesize(sentence_buffer)
                    if audio_b64:
                        yield f"event: audio\ndata: {json.dumps({'base64': audio_b64, 'text': sentence_buffer.strip()})}\n\n"

            latency_ms = int((time.time() - start_time) * 1000)
            yield f"event: done\ndata: {json.dumps({'latency_ms': latency_ms, 'session_id': session_id})}\n\n"

        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ==================== 多模态: 拍照识景 ====================

@app.post("/api/photo-recognize")
async def photo_recognize(request: PhotoRequest):
    """
    拍照识景 —— 多模态识别 + RAG 知识库增强。

    流水线:
      1. 通义千问-VL (DashScope) 识别照片 → 景点名称 + 初步介绍
      2. RAG 知识库检索该景点的详细信息
      3. DeepSeek 整合 VL 识别结果 + RAG 资料 → 完整讲解

    返回:
      {
        "name": "灵山大佛",
        "description": "完整的景点讲解...",
        "vl_raw": "Qwen-VL 原始识别结果",
        "rag_sources": ["来源文件1", ...],
        "enriched": true
      }
    """
    try:
        # === 1. Qwen-VL 多模态识别 (DashScope 原生 SDK) ===
        import dashscope
        from dashscope import MultiModalConversation

        vl_prompt = (
            "请识别这张景点照片。按以下格式回答：\n"
            "1. 景点名称：<具体名称>\n"
            "2. 所属景区：<景区名称>\n"
            "3. 建筑/景观特色：<简要描述>\n"
            "4. 初步介绍：<100-200字的讲解>"
        )

        messages = [{
            "role": "user",
            "content": [
                {"text": vl_prompt},
                {"image": f"data:image/jpeg;base64,{request.image}"}
            ]
        }]

        response = MultiModalConversation.call(
            model="qwen-vl-max",
            messages=messages,
            api_key=CONFIG.dashscope_api_key,
        )

        vl_text = ""
        if response.output and response.output.choices:
            vl_text = response.output.choices[0].message.content[0].get("text", "")

        if not vl_text:
            return {"error": "Qwen-VL 未返回识别结果", "raw": str(response)}

        # === 2. 从 VL 结果中提取景点名称 ===
        spot_name = _extract_spot_name(vl_text)

        # === 3. RAG 检索增强 ===
        rag_sources = []
        enriched_description = vl_text

        if spot_name:
            try:
                retriever = get_retriever()
                rag_result = retriever.retrieve(spot_name, top_k=3)

                if rag_result["docs"] and not rag_result["below_threshold"]:
                    # 拼接 RAG 上下文
                    rag_context = "\n---\n".join(
                        doc.page_content for doc in rag_result["docs"]
                    )
                    rag_sources = rag_result["sources"]

                    # === 4. DeepSeek 整合生成 ===
                    llm = CONFIG.create_llm()
                    integration_prompt = (
                        "你是一个专业的景区导览数字人。请综合以下两方面的信息，"
                        "为游客生成一段生动、详细的景点讲解（200-400字）。\n\n"
                        f"【多模态识别结果】\n{vl_text}\n\n"
                        f"【知识库参考资料】\n{rag_context}\n\n"
                        "要求：口语化、生动有趣、包含关键数据和历史典故。"
                    )
                    llm_result = await llm.ainvoke(integration_prompt)
                    enriched_description = llm_result.content
            except Exception as e:
                print(f"[WARN] RAG 增强失败: {e}")

        return {
            "name": spot_name or "未识别",
            "description": enriched_description,
            "vl_raw": vl_text,
            "rag_sources": rag_sources,
            "enriched": bool(rag_sources),
        }

    except ImportError:
        return {"error": "dashscope SDK 未安装，请运行: pip install dashscope"}
    except Exception as e:
        return {"error": f"多模态识别失败: {str(e)}"}


def _extract_spot_name(vl_text: str) -> str | None:
    """从 Qwen-VL 的识别结果中提取景点名称"""
    import re
    # 匹配 "景点名称：xxx" 或 "**景点名称**：xxx" 等格式
    patterns = [
        r"景点名称[：:]\s*(.+?)(?:\n|$)",
        r"\*\*景点名称\*\*[：:]\s*(.+?)(?:\n|$)",
        r"#*\s*景点名称[：:]\s*(.+?)(?:\n|$)",
    ]
    for pat in patterns:
        match = re.search(pat, vl_text)
        if match:
            name = match.group(1).strip()
            # 清理 markdown 标记
            name = re.sub(r'[*#\[\]]', '', name).strip()
            if name and len(name) < 50:
                return name
    return None


# ==================== 个性化推荐 ====================

@app.get("/api/recommend")
def recommend(
    tags: str = "",
    lat: float | None = None,
    lng: float | None = None,
    db: Session = Depends(get_db),
):
    """
    个性化推荐 —— 根据游客标签推荐路线和讲解重点。
    """
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    routes_pool = {
        "家庭游": {
            "label": "亲子欢乐路线",
            "focus": "重点讲解儿童感兴趣的景点故事和互动体验",
            "spots": ["亲子乐园", "自然生态区", "科普馆", "游船码头"],
        },
        "情侣游": {
            "label": "浪漫打卡路线",
            "focus": "重点讲解景点的浪漫传说和拍照取景点",
            "spots": ["观景台", "花园区", "古桥", "湖心亭"],
        },
        "文化深度游": {
            "label": "文化探索路线",
            "focus": "深入讲解历史典故、建筑风格和文物价值",
            "spots": ["古建筑群", "博物馆", "碑林", "名人故居"],
        },
        "休闲游": {
            "label": "轻松惬意路线",
            "focus": "推荐轻松的游览节奏，重点介绍休息区和景观",
            "spots": ["湖畔步道", "茶室", "花园", "休闲广场"],
        },
    }

    selected = {"label": "经典游览路线", "focus": "全面介绍景区主要景点", "spots": ["主景区", "观景台", "博物馆"]}

    for tag in tag_list:
        if tag in routes_pool:
            selected = routes_pool[tag]
            break

    return {
        "routes": [selected],
        "tags": tag_list,
        "message": f"已根据您的偏好推荐: {selected['label']}"
    }


# ==================== GPS 附近景点 ====================

@app.get("/api/nearby-spots")
async def nearby_spots(
    lat: float,
    lng: float,
    radius: int = 500,
    db: Session = Depends(get_db),
):
    """
    GPS 触发附近景点 —— 返回指定范围内的预设景点。
    """
    from math import radians, cos, sin, asin, sqrt

    def haversine(lat1, lon1, lat2, lon2):
        r = 6371000
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        return r * 2 * asin(sqrt(a))

    db_spots = db.query(ScenicSpot).all()

    nearby = []
    for spot in db_spots:
        dist = haversine(lat, lng, spot.latitude, spot.longitude)
        if dist <= radius:
            nearby.append({
                "name": spot.name,
                "distance_m": round(dist, 0),
                "description": spot.description,
                "category": spot.category,
                "visit_duration": spot.visit_duration,
                "audio_intro_path": spot.audio_intro_path,
            })

    nearby.sort(key=lambda x: x["distance_m"])
    return {"spots": nearby, "center": {"lat": lat, "lng": lng}, "radius": radius}


# ==================== 健康检查 ====================

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "景区导览AI数字人", "version": "2.0.0"}


# ==================== 主程序入口 ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
