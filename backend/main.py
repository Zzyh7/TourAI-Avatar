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
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
import json
import asyncio
from typing import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Depends, Request, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel

import re
from config import CONFIG
from database import init_db, get_db, SessionLocal
from models.schema import ScenicSpot, Session as SessionModel, Conversation
from agents.planner import GuideAgent
from services.tts.doubao_tts import doubao_tts_service as tts_service

# 流式输出过滤：即使 prompt 禁止了，LLM 偶尔还是会生成 markdown/emoji/废话
_OUTPUT_MD_CLEANUP = re.compile(
    r"\*{1,3}(?!\s)"          # **, ***, * (但保留纯星号空格)
    r"|#{1,4}"                # ###, #### 等标题标记
    r"|~~|```|`"              # 删除线、代码块、行内代码
    r"|^---+$|^\*{3,}$"       # 分隔线
    r"|^\d+[\.\)、]\s*",       # 编号列表 (1. 2) 1、)
    re.MULTILINE,
)

# 禁止的开场白/预告短语（LLM 偶尔会说"我来查一下"然后继续输出正文）
_OUTPUT_BAN_PHRASES = re.compile(
    r"(我(来|先)(帮您)?(查|搜|找|确认|获取|检索|看看|了解|搜索)一?下[。！，,]*"
    r"|让我(来)?(查|搜|找|确认|获取|检索|看看|了解|搜索)一?下[。！，,]*"
    r"|正在(为您)?(查|搜|找|获取|检索|搜索|查找)[。！，,]*"
    r"|根据(检索|搜索|查询)结果[，,]*)"
)

def _clean_stream_token(text: str) -> str:
    """过滤流式输出中的 markdown/emoji/废话，清理后如果为空则返回空字符串"""
    text = _OUTPUT_MD_CLEANUP.sub("", text)
    text = _OUTPUT_BAN_PHRASES.sub("", text)
    return text
from services.sentiment.analyzer import SentimentAnalyzer
from admin.knowledge import router as knowledge_router
from admin.config_router import router as config_router
from admin.stats import router as stats_router
from admin.common_dialogue_router import router as common_dialogue_router
from admin.scenic_spots_router import router as scenic_spots_router
from admin.data_router import router as data_router
from admin.analytics import router as analytics_router
from rag_system import rag_router, init_rag, get_retriever
from services.common_dialogue import CommonDialogueService
from services.stt import transcribe


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

    # 2.5 预热 TTS 连接，减少首次语音合成的延迟
    try:
        await asyncio.wait_for(tts_service.warm_up(), timeout=5.0)
    except (asyncio.TimeoutError, Exception):
        print("[WARN] TTS 预热未完成（不影响正常使用）")

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
app.include_router(common_dialogue_router)
app.include_router(scenic_spots_router)
app.include_router(data_router)
app.include_router(analytics_router)

# 注册 RAG 增强知识库路由 (独立 /api/rag/query + /api/rag/admin/upload/faq)
app.include_router(rag_router, prefix="/api/rag")

# 注册 OpenAI 兼容 API (供 Live2D/OpenAvatarChat LLM 调用)
from openai_compat_api import router as openai_compat_router
app.include_router(openai_compat_router)

# 轮播图
@app.get("/carousel/{fname}")
async def carousel_img(fname: str):
    import os
    path = os.path.join("../web/bg", fname)
    if os.path.exists(path):
        return FileResponse(path)
    return Response(status_code=404)

# 静态资源
@app.get("/logo.png")
async def serve_logo():
    return FileResponse("../web/logo.png")

@app.get("/web")
async def serve_competition_web():
    return FileResponse("../web/index.html")

@app.get("/admin")
async def serve_admin():
    return FileResponse("../web/admin.html")

@app.get("/chat")
async def serve_chat():
    return FileResponse("D:/cailin/competition-web/chat.html")

@app.get("/")
async def serve_root():
    return FileResponse("../web/index.html")

# ==================== 工具函数 ====================

def _haversine(lat1, lon1, lat2, lon2):
    """计算两点间的球面距离（米）"""
    from math import radians, cos, sin, asin, sqrt
    r = 6371000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return r * 2 * asin(sqrt(a))


def _strip_emoji(text: str) -> str:
    """去除文本中的 emoji 表情符号"""
    import re
    # 匹配常见 emoji 范围 (Emoticons, Symbols, Pictographs, Transport, etc.)
    emoji_pattern = re.compile(
        "["
        "\U0001F300-\U0001F9FF"  # Misc Symbols, Emoticons, Pictographs
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols Extended-A
        "\U00002600-\U000027BF"  # Misc Symbols
        "\U0000FE00-\U0000FE0F"  # Variation Selectors
        "\U0001F000-\U0001F02F"  # Mahjong Tiles
        "\U0001F0A0-\U0001F0FF"  # Playing Cards
        "\U00002B50"              # ⭐
        "\U00002764"              # ❤
        "\U0000200D"              # Zero Width Joiner
        "\U0001F100-\U0001F1FF"  # Enclosed Alphanumeric Supplement
        "\U00002300-\U000023FF"  # Misc Technical (includes ⌚)
        "\U00002500-\U000025FF"  # Geometric Shapes (includes ▶)
        "\U00002100-\U000021FF"  # Letterlike Symbols (includes ™)
        "\U000000A9"              # ©
        "\U000000AE"              # ®
        "\U0000203C"              # ‼
        "\U00002049"              # ⁉
        "\U00002122"              # ™
        "\U00002139"              # ℹ
        "\U00002328-\U0000232B"  # ⌨-⌫
        "\U000023CF"              # ⏏
        "\U000023E9-\U000023F3"  # ⏩-⏳
        "\U000023F8-\U000023FA"  # ⏸-⏺
        "\U000024C2"              # Ⓜ
        "\U000025AA-\U000025AB"  # ▪-▫
        "\U000025B6"              # ▶
        "\U000025C0"              # ◀
        "\U000025FB-\U000025FE"  # ◻-◾
        "\U00002600-\U000027BF"  # ☀-➿
        "\U00002934-\U00002935"  # ⤴-⤵
        "\U00002B05-\U00002B07"  # ⬅-⬇
        "\U00002B1B-\U00002B1C"  # ⬛-⬜
        "\U00002B50"              # ⭐
        "\U00002B55"              # ⭕
        "\U00003030"              # 〰
        "\U0000303D"              # 〽
        "\U00003297"              # ㊗
        "\U00003299"              # ㊙
        "\U0001F004"              # 🀄
        "\U0001F0CF"              # 🃏
        "\U0001F170-\U0001F251"  # 🅰-🉑
        "\U0001F300-\U0001FAFF"  # 🌀-🫿 (extended range)
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub('', text).strip()


# ==================== 请求/响应模型 ====================

class ChatRequest(BaseModel):
    text: str
    session_id: str = ""


# ==================== 对话日志 & 情感分析 ====================

async def _log_conversation(
    session_id: str,
    user_text: str,
    assistant_text: str,
    latency_ms: int,
):
    """
    保存对话记录并调用 LLM 进行情感分析。
    情感分析设置超时，避免阻塞主流程。
    """
    sentiment = "中性"
    try:
        llm = CONFIG.create_llm()
        analyzer = SentimentAnalyzer(llm)
        # 设置 3 秒超时，避免情感分析拖慢响应
        sentiment = await asyncio.wait_for(analyzer.analyze(user_text), timeout=3.0)
    except (asyncio.TimeoutError, Exception):
        # 超时或失败时使用简单的关键词判断作为降级
        positive_words = ["好", "美", "赞", "喜欢", "开心", "棒", "不错", "谢谢", "厉害", "方便"]
        negative_words = ["差", "烂", "失望", "生气", "垃圾", "坑", "骗", "糟糕", "烦", "慢"]
        text = user_text
        pos_count = sum(1 for w in positive_words if w in text)
        neg_count = sum(1 for w in negative_words if w in text)
        if pos_count > neg_count:
            sentiment = "正面"
        elif neg_count > pos_count:
            sentiment = "负面"
        # else remain "中性"

    db = SessionLocal()
    try:
        now = datetime.utcnow()
        # 保存用户消息
        db.add(Conversation(
            session_id=session_id, role="user", content=user_text,
            sentiment=sentiment, latency_ms=latency_ms, created_at=now,
        ))
        # 保存助手回复
        db.add(Conversation(
            session_id=session_id, role="assistant", content=assistant_text,
            sentiment=sentiment, latency_ms=latency_ms, created_at=now,
        ))
        db.commit()
        print(f"[LOG] 对话已记录 [{sentiment}] {session_id}: {user_text[:30]}...")
    except Exception as e:
        db.rollback()
        print(f"[WARN] 对话记录失败: {e}")
    finally:
        db.close()
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
async def chat(req: Request, chat_req: ChatRequest):
    """
    文本问答 + TTS 语音合成（SSE 流式）—— 支持语音+文本混合输入。

    前端通过 Web Speech API 将语音转为文本后调用此端点。
    后端使用 RAG 检索 + DeepSeek 生成回答，并通过豆包 TTS (火山引擎) 合成语音。

    优化：TTS 合成与 LLM 生成并行进行，避免语音输出不连贯。

    支持打断：客户端断开连接时自动取消 LLM 生成和 TTS 合成。

    返回 SSE 事件流:
      event: token  → 文本 token
      event: audio  → TTS 音频片段 (base64 mp3)
      event: tool   → 工具调用状态 (仅 Agent 模式)
      event: done   → 完成标记
    """
    session_id = chat_req.session_id or uuid.uuid4().hex[:12]
    start_time = time.time()

    async def event_generator() -> AsyncIterator[str]:
        full_answer = ""
        sentence_buffer = ""
        first_audio_sent = False
        cancelled = False
        # TTS 异步任务管理：并行合成，保序输出
        pending_tts: list[dict] = []  # [{order, text, task}]
        tts_order = 0
        next_audio_order = 0

        # 追踪所有 TTS 任务，用于取消时清理
        _tts_tasks: list[asyncio.Task] = []

        async def flush_ready_audio():
            """输出所有已完成的、顺序正确的 TTS 音频"""
            nonlocal next_audio_order
            yielded = []
            for i, item in enumerate(pending_tts):
                if item["task"].done() and item["order"] == next_audio_order:
                    try:
                        audio_b64 = item["task"].result()
                        if audio_b64:
                            yielded.append(
                                f"event: audio\ndata: {json.dumps({'base64': audio_b64, 'text': item['text']})}\n\n"
                            )
                    except Exception:
                        pass
                    next_audio_order += 1
                else:
                    break
            # 清理已输出的项
            for _ in yielded:
                pending_tts.pop(0)
            return yielded

        def fire_tts(text: str):
            """启动后台 TTS 任务，不阻塞当前流"""
            nonlocal tts_order
            if not text.strip():
                return
            task = asyncio.create_task(tts_service.synthesize(text.strip()))
            _tts_tasks.append(task)
            pending_tts.append({"order": tts_order, "text": text.strip(), "task": task})
            tts_order += 1

        def cancel_all_tts():
            """取消所有未完成的 TTS 任务"""
            for t in _tts_tasks:
                if not t.done():
                    t.cancel()

        def maybe_split_first_chunk(text: str) -> tuple[str, str]:
            """
            首句快速分块：在逗号处切分以加快初始音频响应。
            仅对第一次音频使用，后续使用完整句子以保证语调连贯。
            """
            nonlocal first_audio_sent
            if first_audio_sent:
                return text, ""
            if any(punct in text for punct in "。！？\n"):
                # 已经是完整句，不分块
                return text, ""
            first_phrase, remaining = tts_service.split_first_phrase(text, min_chars=12)
            if remaining:
                first_audio_sent = True
            return first_phrase, remaining

        async def handle_sentence_end():
            """处理句子结束：启动 TTS + 检查并输出已完成音频"""
            nonlocal sentence_buffer, first_audio_sent
            if not sentence_buffer.strip():
                return

            # 首句快速分块
            first_chunk, rest = maybe_split_first_chunk(sentence_buffer)
            if first_chunk:
                fire_tts(first_chunk)
            sentence_buffer = rest if rest else ""

            if not rest:
                # 如果是完整句（非分块），标记首音已发
                first_audio_sent = True

            # 输出所有已完成且顺序正确的音频
            for event_str in await flush_ready_audio():
                yield event_str

        async def check_disconnect() -> bool:
            """检查客户端是否断开连接"""
            nonlocal cancelled
            if cancelled:
                return True
            try:
                if await req.is_disconnected():
                    cancelled = True
                    return True
            except Exception:
                pass
            return False

        try:
            # === 常用对话匹配：命中则直接返回预设回答，不走 LLM ===
            cd_matched = None
            try:
                from database import SessionLocal
                cd_db = SessionLocal()
                try:
                    cd_service = CommonDialogueService()
                    cd_matched = cd_service.match(chat_req.text, cd_db)
                finally:
                    cd_db.close()
            except Exception as e:
                print(f"[CD] 常用对话匹配出错: {e}")

            if cd_matched:
                # 预设回答直接逐字输出 + TTS（过滤 emoji）
                cd_answer = _strip_emoji(cd_matched.answer)
                for char in cd_answer:
                    if await check_disconnect():
                        break
                    char = _clean_stream_token(char)
                    if not char:
                        continue
                    full_answer += char
                    sentence_buffer += char
                    yield f"event: token\ndata: {json.dumps({'text': char})}\n\n"

                    if any(punct in char for punct in "。！？\n"):
                        async for audio_event in handle_sentence_end():
                            yield audio_event
                    elif any(punct in char for punct in "，、,") and len(sentence_buffer) >= 12 and not first_audio_sent:
                        async for audio_event in handle_sentence_end():
                            yield audio_event

                    for event_str in await flush_ready_audio():
                        yield event_str

                if not cancelled:
                    # 处理末尾残句
                    if sentence_buffer.strip():
                        fire_tts(sentence_buffer)
                    if pending_tts:
                        await asyncio.gather(*[item["task"] for item in pending_tts], return_exceptions=True)
                    for audio_event in await flush_ready_audio():
                        yield audio_event

                    latency_ms = int((time.time() - start_time) * 1000)
                    yield f"event: done\ndata: {json.dumps({'latency_ms': latency_ms, 'session_id': session_id, 'source': 'common_dialogue'})}\n\n"
                return

            if guide_agent is not None:
                # === Agent 模式: GuideAgent (MCP工具 + RAG) ===
                async for event in guide_agent.stream(chat_req.text, session_id):
                    # 检查客户端是否断开
                    if await check_disconnect():
                        break

                    if event["type"] == "token":
                        token = _strip_emoji(event["data"])
                        if not token:
                            continue
                        full_answer += token
                        sentence_buffer += token
                        yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"

                        if any(punct in token for punct in "。！？\n"):
                            async for audio_event in handle_sentence_end():
                                yield audio_event
                        elif any(punct in token for punct in "，、,") and len(sentence_buffer) >= 12 and not first_audio_sent:
                            # 首句逗号处分块，快速启动音频
                            async for audio_event in handle_sentence_end():
                                yield audio_event

                    elif event["type"] == "tool_start":
                        yield f"event: tool\ndata: {json.dumps({'status': 'start', 'label': event['data']['label']})}\n\n"
                    elif event["type"] == "done":
                        # 处理末尾残句
                        if sentence_buffer.strip():
                            fire_tts(sentence_buffer)
                            sentence_buffer = ""
                        # 等待所有 TTS 任务完成
                        if pending_tts:
                            await asyncio.gather(*[item["task"] for item in pending_tts], return_exceptions=True)
                        for audio_event in await flush_ready_audio():
                            yield audio_event
                        break

                    # 每个 token 后检查是否有音频就绪
                    for event_str in await flush_ready_audio():
                        yield event_str
            else:
                # === Direct RAG + LLM 模式 ===
                retriever = get_retriever()
                rag_result = retriever.retrieve(chat_req.text, top_k=5)
                context = "\n---\n".join(
                    doc.page_content for doc in rag_result.get("docs", [])
                ) if rag_result.get("docs") else "暂无相关资料"

                llm = CONFIG.create_llm()
                prompt = (
                    "你是一个专业的景区导览数字人，名叫小导。请基于【参考资料】回答问题。\n"
                    "如果参考资料不足以回答，请直接说「资料中没有相关信息」，不要编造。\n\n"
                    f"【用户问题】：{chat_req.text}\n\n"
                    f"【参考资料】：\n{context}"
                )
                async for chunk in llm.astream(prompt):
                    # 检查客户端是否断开
                    if await check_disconnect():
                        break

                    token = chunk.content if hasattr(chunk, 'content') else str(chunk)
                    token = _strip_emoji(token)
                    if token:
                        token = _clean_stream_token(token)
                        if not token:
                            continue
                        full_answer += token
                        sentence_buffer += token
                        yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"

                        if any(punct in token for punct in "。！？\n"):
                            async for audio_event in handle_sentence_end():
                                yield audio_event
                        elif any(punct in token for punct in "，、,") and len(sentence_buffer) >= 12 and not first_audio_sent:
                            async for audio_event in handle_sentence_end():
                                yield audio_event

                    # 每个 token 后检查是否有音频就绪
                    for event_str in await flush_ready_audio():
                        yield event_str

                # 如果没有被取消，处理末尾残句
                if not cancelled:
                    if sentence_buffer.strip():
                        fire_tts(sentence_buffer)
                    # 等待所有 TTS 任务完成
                    if pending_tts:
                        await asyncio.gather(*[item["task"] for item in pending_tts], return_exceptions=True)
                    for audio_event in await flush_ready_audio():
                        yield audio_event

            if not cancelled:
                latency_ms = int((time.time() - start_time) * 1000)
                # 保存对话记录 + 情感分析（带超时，不影响done事件）
                await _log_conversation(session_id, chat_req.text, full_answer, latency_ms)
                yield f"event: done\ndata: {json.dumps({'latency_ms': latency_ms, 'session_id': session_id})}\n\n"

        except asyncio.CancelledError:
            # 客户端断开时，Starlette 取消生成器任务
            cancelled = True
        except Exception as e:
            if not cancelled:
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
        finally:
            # 清理：取消所有未完成的 TTS 任务
            cancel_all_tts()
            if _tts_tasks:
                await asyncio.gather(*_tts_tasks, return_exceptions=True)

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
        "自然风光": {
            "label": "山水精华线",
            "focus": "涵盖景区核心自然景观，适合户外与摄影爱好者",
            "spots": ["灵山大佛", "九龙灌浴", "曼飞龙塔", "拈花湾"],
        },
        "历史人文": {
            "label": "文化探索线",
            "focus": "深度体验佛教文化和历史建筑群，讲解历史典故",
            "spots": ["古建筑群", "大殿", "碑林", "寺庙遗址"],
        },
        "亲子游乐": {
            "label": "亲子欢乐线",
            "focus": "轻松有趣的家庭出游路线，寓教于乐",
            "spots": ["亲子乐园", "自然生态区", "互动体验区", "游船码头"],
        },
        "文创打卡": {
            "label": "文创打卡线",
            "focus": "文艺范十足的精美打卡路线，适合拍照分享",
            "spots": ["文创街区", "观景台", "花园广场", "地标打卡点"],
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
    db_spots = db.query(ScenicSpot).all()

    nearby = []
    for spot in db_spots:
        dist = _haversine(lat, lng, spot.latitude, spot.longitude)
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


# ==================== GPS 触发讲解检测 ====================

@app.get("/api/gps/check")
def gps_trigger_check(
    lat: float,
    lng: float,
    visited: str = "",
    db: Session = Depends(get_db),
):
    """
    GPS 触发检测 —— 检查用户是否进入了某个景点的触发范围。
    前端每5秒轮询此接口，当用户进入新景点的 trigger_radius 时返回触发信息。

    参数:
      lat, lng: 用户当前 GPS 坐标
      visited: 逗号分隔的已触发景点名称列表（避免重复触发）

    返回:
      {"triggered": true, "spot": {...}} 或 {"triggered": false}
    """
    visited_set = set(v.strip() for v in visited.split(",") if v.strip())

    spots = db.query(ScenicSpot).all()
    for spot in spots:
        if not spot.latitude or not spot.longitude:
            continue
        if spot.name in visited_set:
            continue

        d = _haversine(lat, lng, spot.latitude, spot.longitude)
        radius = spot.trigger_radius or 100

        if d <= radius:
            return {
                "triggered": True,
                "spot": {
                    "name": spot.name,
                    "distance_m": round(d),
                    "description": spot.description,
                    "category": spot.category or "",
                    "visit_duration": spot.visit_duration or 10,
                },
            }

    return {"triggered": False}


# ==================== 语音识别 (STT) ====================

@app.post("/api/stt")
async def speech_to_text(audio: UploadFile = File(...), mime_type: str = Form(default="audio/wav")):
    """
    语音转文字 —— 使用 DashScope Paraformer。
    前端录制音频后上传，返回识别的文字。

    参数:
      - audio: 音频文件 (multipart/form-data)
      - mime_type: 音频 MIME 类型 (如 audio/wav, audio/webm)

    返回:
      {"text": "识别的文字内容", "success": true}
    """
    try:
        audio_data = await audio.read()
        if not audio_data or len(audio_data) < 100:
            return JSONResponse({"text": "", "success": False, "error": "音频数据为空"}, status_code=400)

        # 优先使用上传文件的 content_type
        actual_mime = audio.content_type or mime_type
        result = transcribe(audio_data, actual_mime)
        return result

    except Exception as e:
        return JSONResponse({"text": "", "success": False, "error": str(e)}, status_code=500)


# ==================== 健康检查 ====================

class TTSRequest(BaseModel):
    text: str
    voice: str = "BV700_streaming"

@app.post("/api/tts")
async def text_to_speech(req: TTSRequest):
    """豆包 TTS — 文本转语音，返回 MP3 音频"""
    import base64 as b64, httpx as _httpx, uuid as _uuid
    try:
        text = req.text.strip()
        if not text:
            return JSONResponse({"error": "empty text"}, status_code=400)
        payload = {
            "app": {"appid": CONFIG.doubao_tts_appid, "token": CONFIG.doubao_tts_api_key, "cluster": "volcano_tts"},
            "user": {"uid": "live2d_user"},
            "audio": {"voice_type": req.voice, "encoding": "mp3"},
            "request": {"reqid": _uuid.uuid4().hex, "text": text, "text_type": "plain", "operation": "query", "with_frontend": 1},
        }
        headers = {"Authorization": f"Bearer;{CONFIG.doubao_tts_api_key}", "Content-Type": "application/json"}
        async with _httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(CONFIG.doubao_tts_endpoint, json=payload, headers=headers)
            if resp.status_code != 200:
                return JSONResponse({"error": f"Doubao HTTP {resp.status_code}: {resp.text[:200]}"}, status_code=500)
            result = resp.json()
            if result.get("code") != 3000:
                return JSONResponse({"error": result.get("message", str(result))}, status_code=500)
            audio_b64 = result.get("data", "")
            if not audio_b64:
                return JSONResponse({"error": "empty audio"}, status_code=500)
            audio_bytes = b64.b64decode(audio_b64)
            return Response(content=audio_bytes, media_type="audio/mp3")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "景区导览AI数字人", "version": "2.0.0"}


# ==================== 主程序入口 ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
