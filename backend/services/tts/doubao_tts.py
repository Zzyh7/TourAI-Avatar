"""
豆包语音合成 (Doubao TTS) —— 火山引擎 BytePlus Seed Speech，异步调用，支持分句合成。
"""
import asyncio
import io
import base64
import re
import uuid
import logging
from typing import AsyncIterator
import aiohttp
from config import CONFIG

logger = logging.getLogger(__name__)

# 中文分句正则
_SENTENCE_END = re.compile(r"[。！？；\n]")
# 短停顿标点（逗号等），用于首句快速分块
_PHRASE_END = re.compile(r"[，、,]")

# TTS 朗读前需要清理的符号（这些符号不应该被朗读出来）
_TTS_CLEANUP = re.compile(r"[\U0001F300-\U0001FAFF]|"       # emoji 表情
                          r"[☀-➿]|"               # 杂项符号/装饰符
                          r"[~*#_>`]|"                       # markdown 标记符号
                          r"^---+$|"                         # 分隔线
                          r"^\*{3,}$",                       # 星号分隔线
                          re.MULTILINE)


def _clean_text_for_tts(text: str) -> str:
    """移除 TTS 不应朗读的符号：emoji、markdown 标记、装饰线等"""
    cleaned = _TTS_CLEANUP.sub("", text)
    cleaned = re.sub(r"\n{2,}", "\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


# 豆包 TTS 可用音色（已实测验证）
DOUBAO_VOICES = {
    "BV700_streaming": "灿灿 2.0 女声",
    "BV701_streaming": "灿灿 2.0 男声",
    "BV001_streaming": "甜美女生",
    "BV002_streaming": "知性女生",
    "BV004_streaming": "阳光男声",
    "BV005_streaming": "温柔女声",
    "BV411_streaming": "小帅解说 (男)",
    "BV412_streaming": "小美解说 (女)",
    "zh_male_M392_conversation_wvae_bigtts": "对话男声",
    "zh_female_wanwanxiaohe_moon_bigtts": "湾湾小何 (女)",
    "zh_male_shaonianzixin_uranus_bigtts": "少年自信 (收藏音色)",
}

# 与 Edge-TTS 音色的兼容映射
EDGE_TO_DOUBAO_MAP = {
    "zh-CN-XiaoxiaoNeural":  "zh_female_qingxin",
    "zh-CN-YunxiNeural":     "BV001_streaming",
    "zh-CN-YunjianNeural":   "BV003_streaming",
    "zh-CN-XiaoyiNeural":    "BV005_streaming",
    "zh-CN-YunyangNeural":   "BV701_streaming",
    "zh-CN-XiaochenNeural":  "BV700_streaming",
    "zh-CN-XiaohanNeural":   "BV002_streaming",
    "zh-CN-XiaomoNeural":    "zh_female_qingxin",
    "zh-CN-XiaoqiuNeural":   "BV002_streaming",
    "zh-CN-XiaorouNeural":   "BV005_streaming",
}


class DoubaoTTS:
    """
    豆包语音合成服务 (基于火山引擎 openspeech API)。

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

    def __init__(self, api_key: str = None, voice: str = None, appid: str = None):
        self.api_key = api_key or CONFIG.doubao_tts_api_key
        self.voice = voice or CONFIG.doubao_tts_voice
        self.appid = appid or CONFIG.doubao_tts_appid
        self.endpoint = CONFIG.doubao_tts_endpoint
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=10, force_close=False)
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def warm_up(self):
        """预热 TTS 连接，减少首次调用延迟"""
        try:
            await self.synthesize("你好")
            logger.info("Doubao-TTS 预热完成")
        except Exception as e:
            logger.warning(f"Doubao-TTS 预热失败（不影响正常使用）: {e}")

    async def _call_api(self, text: str, voice: str = None) -> str:
        """
        调用豆包 TTS API 合成单段文本。

        返回: base64 编码的 mp3 音频数据
        """
        if not text.strip():
            return ""

        reqid = uuid.uuid4().hex
        actual_voice = voice or self.voice

        payload = {
            "app": {
                "appid": self.appid,
                "token": self.api_key,
                "cluster": "volcano_tts",
            },
            "user": {
                "uid": "travel_agent_user",
            },
            "audio": {
                "voice_type": actual_voice,
                "encoding": "mp3",
            },
            "request": {
                "reqid": reqid,
                "text": _clean_text_for_tts(text),
                "text_type": "plain",
                "operation": "query",
                "with_frontend": 1,
            },
        }

        session = await self._get_session()
        headers = {
            "Authorization": f"Bearer;{self.api_key}",
            "Content-Type": "application/json",
        }

        async with session.post(self.endpoint, json=payload, headers=headers) as resp:
            result = await resp.json()

            if resp.status != 200:
                msg = result.get('message', str(result))
                if "grant not found" in msg.lower():
                    raise Exception(
                        f"豆包 TTS 服务未开通 (HTTP {resp.status})。请前往火山引擎控制台开通语音合成服务：\n"
                        f"  1. 访问 https://console.volcengine.com/speech/service/8\n"
                        f"  2. 创建语音合成应用，获取 AppID 和 Token\n"
                        f"  3. 在 .env 中设置 DOUBAO_TTS_APPID=你的AppID"
                    )
                raise Exception(f"豆包 TTS HTTP {resp.status}: {msg}")

            code = result.get("code")
            if code != 3000:
                msg = result.get('message', str(result))
                if "grant not found" in msg.lower():
                    raise Exception(
                        f"豆包 TTS 服务未开通 (code={code})。请前往火山引擎控制台开通语音合成服务：\n"
                        f"  1. 访问 https://console.volcengine.com/speech/service/8\n"
                        f"  2. 创建语音合成应用，获取 AppID 和 Token\n"
                        f"  3. 在 .env 中设置 DOUBAO_TTS_APPID=你的AppID"
                    )
                raise Exception(f"豆包 TTS 返回错误 (code={code}): {msg}")

            audio_b64 = result.get("data", "")
            if not audio_b64:
                raise Exception("豆包 TTS 返回空音频数据")

            return audio_b64

    async def synthesize(self, text: str, voice: str = None) -> str:
        """
        合成单段文本为语音，返回 base64 编码的 mp3。

        返回: base64 字符串，前端可用 data:audio/mp3;base64,xxx 直接播放
        """
        if not text.strip():
            return ""
        return await self._call_api(text, voice)

    async def synthesize_stream_bytes(self, text: str, voice: str = None) -> AsyncIterator[str]:
        """
        流式合成：逐音频块 yield base64 编码的数据。

        注意：豆包 API 非流式 HTTP 接口返回完整音频，这里按句分块模拟流式。
        如需真正的流式，需使用 WebSocket 接口。

        yield: base64 编码的原始音频数据块
        """
        if not text.strip():
            return
        audio_b64 = await self._call_api(text, voice)
        if audio_b64:
            yield audio_b64

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


# 模块级单例
doubao_tts_service = DoubaoTTS()
