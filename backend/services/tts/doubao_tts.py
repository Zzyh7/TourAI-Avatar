"""
豆包语音合成 (Doubao TTS) —— 火山引擎 Seed-TTS-2.0，WebSocket 双向流式协议。
"""
import asyncio
import base64
import json
import re
import struct
import uuid
import logging
from typing import AsyncIterator

import websockets
from websockets.exceptions import WebSocketException

from config import CONFIG

logger = logging.getLogger(__name__)

# WebSocket V3 端点
_TTS_URL = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"

# 中文分句正则
_SENTENCE_END = re.compile(r"[。！？；\n]")
_PHRASE_END = re.compile(r"[，、,]")

# TTS 朗读前需要清理的符号
_TTS_CLEANUP = re.compile(
    r"[\U0001F300-\U0001FAFF]|"
    r"[☀-➿]|"
    r"[~*#_>`]|"
    r"^---+$|"
    r"^\*{3,}$",
    re.MULTILINE,
)

# 豆包 TTS 可用音色（Seed-TTS-2.0 WebSocket，已实测验证）
DOUBAO_VOICES = {
    # --- 2026-07 实测通过 ---
    "zh_female_vv_uranus_bigtts": "Vivi 2.0 女声（默认）",
    "zh_male_shaonianzixin_uranus_bigtts": "少年自信 (男)",
    "zh_male_tiancaitongsheng_mars_bigtts": "天才童声 (男)",
    # --- 以下为 seed-tts-2.0 官方音色，待验证 ---
    "zh_female_xiaohe_uranus_bigtts": "Mindy 女声",
    "zh_male_m191_uranus_bigtts": "Kian 男声",
    "zh_male_taocheng_uranus_bigtts": "Cedric 男声",
    "zh_female_shuangkuaisisi_moon_bigtts": "新闻播报女声",
    "zh_male_yuanboxiaoshu_moon_bigtts": "温暖男主播",
}

# 与 Edge-TTS 音色的兼容映射
EDGE_TO_DOUBAO_MAP = {
    "zh-CN-XiaoxiaoNeural": "zh_female_vv_uranus_bigtts",
    "zh-CN-YunxiNeural": "zh_female_vv_uranus_bigtts",
    "zh-CN-YunjianNeural": "zh_male_m191_uranus_bigtts",
    "zh-CN-XiaoyiNeural": "zh_female_xiaohe_uranus_bigtts",
    "zh-CN-YunyangNeural": "zh_male_shaonianzixin_uranus_bigtts",
    "zh-CN-XiaochenNeural": "zh_female_vv_uranus_bigtts",
    "zh-CN-XiaohanNeural": "zh_female_xiaohe_uranus_bigtts",
    "zh-CN-XiaomoNeural": "zh_female_vv_uranus_bigtts",
    "zh-CN-XiaoqiuNeural": "zh_female_xiaohe_uranus_bigtts",
    "zh-CN-XiaorouNeural": "zh_female_vv_uranus_bigtts",
}


def _clean_text_for_tts(text: str) -> str:
    """移除 TTS 不应朗读的符号：emoji、markdown 标记、装饰线等"""
    cleaned = _TTS_CLEANUP.sub("", text)
    cleaned = re.sub(r"\n{2,}", "\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


# ======================================================================
# WebSocket 二进制协议（Seed-TTS-2.0 bidirectional）
# ======================================================================

def _build_headers(api_key: str) -> dict[str, str]:
    return {
        "X-Api-Key": api_key,
        "X-Api-Resource-Id": "seed-tts-2.0",
        "X-Api-Request-Id": str(uuid.uuid4()),
        "X-Api-Connect-Id": str(uuid.uuid4()),
    }


def _build_frame(
    msg_type: int,
    flag: int,
    event: int = 0,
    session_id: str = "",
    payload: bytes = b"{}",
) -> bytes:
    """
    构建 WebSocket 二进制帧。

    msg_type: 1=FullClientRequest, 2=AudioOnlyClient
    flag: 4=WithEvent, 1=PosSeq, 3=NegSeq
    """
    hdr = bytes([0x11, (msg_type << 4) | flag, 0x10, 0x00])
    body = b""
    if flag == 4:  # WithEvent
        body += struct.pack(">i", event)
        if event not in (1, 2, 50, 51, 52):  # 非 Connection 事件需要 session_id
            sid = session_id.encode("utf-8")
            body += struct.pack(">I", len(sid)) + sid
    body += struct.pack(">I", len(payload)) + payload
    return hdr + body


# 连接事件编号（不需要 session_id）
_CONNECTION_EVENTS = frozenset({1, 2, 50, 51, 52})


def _parse_audio_payload(frame: bytes) -> bytes | None:
    """
    从服务端 AudioOnlyServer 帧中提取音频数据。
    返回 None 表示不是音频帧或解析失败。
    """
    if len(frame) < 4:
        return None
    mtype = (frame[1] >> 4) & 0x0F
    flag = frame[1] & 0x0F
    if mtype != 0x0B:  # AudioOnlyServer
        return None
    pos = 4  # 跳过 header
    if flag == 4:  # WithEvent — Seed-TTS-2.0 音频帧用此标记
        if pos + 4 > len(frame):
            return None
        event = struct.unpack(">i", frame[pos:pos + 4])[0]
        pos += 4
        if event not in _CONNECTION_EVENTS:
            # 跳过 session_id (4 字节长度 + N 字节内容)
            if pos + 4 > len(frame):
                return None
            sid_len = struct.unpack(">I", frame[pos:pos + 4])[0]
            pos += 4 + sid_len
    elif flag in (1, 3):  # PosSeq / NegSeq → 跳过 4 字节 sequence
        pos += 4
    # flag == 2 (LastNoSeq): 无额外字段
    if pos + 4 > len(frame):
        return None
    plen = struct.unpack(">I", frame[pos:pos + 4])[0]
    pos += 4
    if plen > 0 and pos + plen <= len(frame):
        return frame[pos:pos + plen]
    return None


def _parse_event(frame: bytes) -> int | None:
    """从 FullServerResponse 帧提取 event 编号"""
    if len(frame) < 8:
        return None
    mtype = (frame[1] >> 4) & 0x0F
    if mtype != 0x09:  # FullServerResponse
        return None
    return struct.unpack(">i", frame[4:8])[0]


def _is_error_frame(frame: bytes) -> tuple[bool, int, str]:
    """检查是否是 Error 帧，返回 (is_error, code, message)"""
    if len(frame) < 8:
        return False, 0, ""
    mtype = (frame[1] >> 4) & 0x0F
    if mtype != 0x0F:  # Error
        return False, 0, ""
    code = struct.unpack(">I", frame[4:8])[0] if len(frame) >= 8 else 0
    msg = frame[8:].decode("utf-8", errors="replace") if len(frame) > 8 else ""
    return True, code, msg


# ======================================================================
# DoubaoTTS
# ======================================================================


class DoubaoTTS:
    """
    豆包语音合成服务 (基于火山引擎 Seed-TTS-2.0 WebSocket 双向流式协议)。

    用法:
        tts = DoubaoTTS()

        # 单句合成
        audio_b64 = await tts.synthesize("欢迎来到西湖景区")

        # 分句流式合成
        async for sentence, audio_b64 in tts.synthesize_stream("长文本..."):
            ...

        # 流式原始字节（用于 SSE 渐进传输）
        async for chunk_b64 in tts.synthesize_stream_bytes("..."):
            ...
    """

    def __init__(
        self,
        api_key: str = None,
        voice: str = None,
        speed_ratio: float = None,
    ):
        self.api_key = api_key or CONFIG.doubao_tts_api_key
        self.voice = voice or CONFIG.doubao_tts_voice
        self.speed_ratio = speed_ratio if speed_ratio is not None else CONFIG.doubao_tts_speed_ratio

    @property
    def _speech_rate(self) -> int:
        """将 speed_ratio (1.0=正常) 转换为 speech_rate (-50~100, 整数百分比偏移)"""
        rate = round((self.speed_ratio - 1.0) * 100)
        return max(-50, min(100, rate))

    async def warm_up(self):
        """预热 TTS 连接，减少首次调用延迟"""
        try:
            await self.synthesize("你好")
            logger.info("Doubao-TTS (V3 WS) 预热完成")
        except Exception as e:
            logger.warning(f"Doubao-TTS 预热失败（不影响正常使用）: {e}")

    # ------------------------------------------------------------------
    # 核心 WebSocket 调用
    # ------------------------------------------------------------------

    async def _http_v1_synthesize(self, text: str, voice: str) -> bytes:
        """V1 HTTP API 回退（用于 V3 不支持的音色，如 mars_bigtts 系列）"""
        import httpx
        v1_key = CONFIG.doubao_tts_v1_api_key or self.api_key
        payload = {
            "app": {"appid": CONFIG.doubao_tts_appid, "token": v1_key, "cluster": "volcano_tts"},
            "user": {"uid": "travel_agent_user"},
            "audio": {"voice_type": voice, "encoding": "mp3"},
            "request": {"reqid": uuid.uuid4().hex, "text": _clean_text_for_tts(text), "text_type": "plain", "operation": "query"},
        }
        headers = {"X-Api-Key": v1_key, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post("https://openspeech.bytedance.com/api/v1/tts", json=payload, headers=headers)
            if resp.status_code != 200:
                raise Exception(f"豆包 TTS V1 HTTP {resp.status_code}: {resp.text[:200]}")
            result = resp.json()
            if result.get("code") != 3000:
                raise Exception(f"豆包 TTS V1 错误 (code={result.get('code')}): {result.get('message', result)}")
            audio_b64 = result.get("data", "")
            if not audio_b64:
                raise Exception("豆包 TTS V1 返回空音频")
            return base64.b64decode(audio_b64)

    async def _ws_synthesize(self, text: str, voice: str = None) -> bytes:
        """
        通过 WebSocket V3 合成单段文本，返回原始 MP3 字节。
        V3 不支持的音色自动回退到 V1 HTTP。
        """
        if not text.strip():
            return b""

        actual_voice = voice or self.voice
        cleaned_text = _clean_text_for_tts(text)
        headers = _build_headers(self.api_key)
        session_id = str(uuid.uuid4())

        req_params = {
            "speaker": actual_voice,
            "audio_params": {
                "format": "mp3",
                "sample_rate": 24000,
                "speech_rate": self._speech_rate,
            },
        }

        logger.debug("TTS WS: connecting (session=%s, speaker=%s)", session_id, actual_voice)

        try:
            ws = await asyncio.wait_for(
                websockets.connect(
                    _TTS_URL,
                    additional_headers=headers,
                    max_size=16 * 1024 * 1024,
                    open_timeout=15,
                    ping_interval=20,
                    ping_timeout=20,
                ),
                timeout=15,
            )
        except asyncio.TimeoutError:
            raise Exception("豆包 TTS WebSocket 连接超时，请检查网络")
        except WebSocketException as e:
            msg = str(e)
            if "401" in msg or "403" in msg:
                raise Exception(f"豆包 TTS 鉴权失败 (401/403)，请检查 DOUBAO_TTS_API_KEY")
            raise Exception(f"豆包 TTS WebSocket 握手失败: {e}")

        try:
            # 1. StartConnection
            await ws.send(_build_frame(1, 4, event=1))
            msg = await asyncio.wait_for(ws.recv(), timeout=10)
            if _parse_event(msg) != 50:
                err, code, errmsg = _is_error_frame(msg)
                if err:
                    raise Exception(f"豆包 TTS 连接失败 (code={code}): {errmsg}")
                raise Exception(f"豆包 TTS 连接握手异常")

            # 2. StartSession
            start_req = {
                "user": {"uid": headers["X-Api-Request-Id"]},
                "namespace": "BidirectionalTTS",
                "req_params": req_params,
                "event": 100,
            }
            await ws.send(_build_frame(
                1, 4, event=100, session_id=session_id,
                payload=json.dumps(start_req, ensure_ascii=False).encode("utf-8"),
            ))
            msg = await asyncio.wait_for(ws.recv(), timeout=10)
            if _parse_event(msg) != 150:
                err, code, errmsg = _is_error_frame(msg)
                if err:
                    if code == 55000000:
                        logger.info("TTS: voice '%s' not in V3, falling back to V1", actual_voice)
                        await ws.close()
                        return await self._http_v1_synthesize(cleaned_text, actual_voice)
                    raise Exception(f"豆包 TTS 会话启动失败 (code={code}): {errmsg}")
                raise Exception(f"豆包 TTS 会话启动异常")

            # 3. TaskRequest（发送文本）
            task_req = {
                "user": {"uid": headers["X-Api-Request-Id"]},
                "namespace": "BidirectionalTTS",
                "req_params": {**req_params, "text": cleaned_text},
                "event": 200,
            }
            await ws.send(_build_frame(
                1, 4, event=200, session_id=session_id,
                payload=json.dumps(task_req, ensure_ascii=False).encode("utf-8"),
            ))

            # 检查 TaskRequest 的响应（可能直接返回音色不可用错误）
            try:
                check = await asyncio.wait_for(ws.recv(), timeout=5)
                is_err, code, errmsg = _is_error_frame(check)
                if is_err and code == 55000000:
                    await ws.close()
                    logger.info("TTS: voice '%s' not in V3, falling back to V1", actual_voice)
                    return await self._http_v1_synthesize(cleaned_text, actual_voice)
                # 不是错误帧或不是音色错误，放回处理
                if not is_err:
                    audio = _parse_audio_payload(check)
                    if audio:
                        audio_chunks.append(audio)
            except asyncio.TimeoutError:
                pass  # 无立即响应，正常继续接收

            # 4. FinishSession（通知服务端文本发送完毕）
            await ws.send(_build_frame(1, 4, event=102, session_id=session_id))

            # 5. 接收音频
            audio_chunks: list[bytes] = []
            while True:
                try:
                    frame = await asyncio.wait_for(ws.recv(), timeout=30)
                except asyncio.TimeoutError:
                    logger.warning("TTS WS: 等待音频超时")
                    break

                # 检查错误
                is_err, code, errmsg = _is_error_frame(frame)
                if is_err:
                    if code == 55000000:
                        logger.info("TTS: voice '%s' not in V3, falling back to V1", actual_voice)
                        await ws.close()
                        return await self._http_v1_synthesize(cleaned_text, actual_voice)
                    raise Exception(f"豆包 TTS 合成失败 (code={code}): {errmsg}")

                # 提取音频
                audio = _parse_audio_payload(frame)
                if audio:
                    audio_chunks.append(audio)
                    continue

                # 检查是否结束
                event = _parse_event(frame)
                if event in (152, 359):  # SessionFinished / TTSEnded
                    logger.debug("TTS WS: 合成完成 (event=%d, bytes=%d)", event, sum(len(c) for c in audio_chunks))
                    break

            # 6. FinishConnection
            await ws.send(_build_frame(1, 4, event=2))
            try:
                await asyncio.wait_for(ws.recv(), timeout=5)
            except (asyncio.TimeoutError, WebSocketException):
                pass

        finally:
            with __import__("contextlib").suppress(WebSocketException):
                await ws.close()

        if not audio_chunks:
            raise Exception("豆包 TTS 返回空音频数据")

        return b"".join(audio_chunks)

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    async def synthesize(self, text: str, voice: str = None) -> str:
        """
        合成单段文本为语音，返回 base64 编码的 mp3。

        返回: base64 字符串，前端可用 data:audio/mp3;base64,xxx 直接播放
        """
        if not text.strip():
            return ""
        audio_bytes = await self._ws_synthesize(text, voice)
        return base64.b64encode(audio_bytes).decode("utf-8")

    async def synthesize_stream_bytes(self, text: str, voice: str = None) -> AsyncIterator[str]:
        """
        流式合成：逐句合成，yield base64 编码的音频块。

        yield: base64 编码的原始音频数据块
        """
        if not text.strip():
            return
        audio_bytes = await self._ws_synthesize(text, voice)
        if audio_bytes:
            yield base64.b64encode(audio_bytes).decode("utf-8")

    async def synthesize_stream(self, text: str, voice: str = None) -> AsyncIterator[tuple[str, str]]:
        """
        分句合成：按句子切分文本，逐句合成并 yield。

        yield: (sentence_text, audio_base64)
        """
        sentences = self._split_sentences(text)
        for sentence in sentences:
            if not sentence.strip():
                continue
            audio_b64 = await self.synthesize(sentence, voice)
            yield sentence, audio_b64

    def _split_sentences(self, text: str) -> list[str]:
        """按中文标点分句"""
        result = []
        current = ""
        for char in text:
            current += char
            if _SENTENCE_END.match(char):
                if current.strip():
                    result.append(current.strip())
                current = ""
        if current.strip():
            result.append(current.strip())
        return result if result else [text]

    def split_first_phrase(self, text: str, min_chars: int = 15) -> tuple[str, str]:
        """
        从文本中切分出首短语用于快速首音。

        优先在逗号处切分，其次在最短句末标点处切分。
        如果文本太短则整体作为首短语。

        返回: (first_phrase, remaining_text)
        """
        text = text.strip()
        if len(text) <= min_chars:
            return text, ""

        for match in _PHRASE_END.finditer(text):
            end = match.end()
            if end >= min_chars:
                return text[:end].strip(), text[end:].strip()

        for match in _SENTENCE_END.finditer(text):
            end = match.end()
            return text[:end].strip(), text[end:].strip()

        return text, ""

    async def close(self):
        """WebSocket 客户端无需显式关闭（每次调用后自动断开）"""
        pass


# 模块级单例
doubao_tts_service = DoubaoTTS()
