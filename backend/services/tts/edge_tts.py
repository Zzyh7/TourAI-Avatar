"""
Edge-TTS 语音合成 —— 微软免费 TTS 服务，异步调用，支持分句合成。
"""
import asyncio
import io
import base64
import re
import logging
from typing import AsyncIterator
import edge_tts
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
    # 清理多余空白
    cleaned = re.sub(r"\n{2,}", "\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


class EdgeTTSService:
    """
    微软 Edge TTS 语音合成服务。

    用法:
        tts = EdgeTTSService()

        # 单句合成
        audio_b64 = await tts.synthesize("欢迎来到西湖景区")

        # 分句流式合成
        async for sentence, audio_b64 in tts.synthesize_stream("长文本..."):
            ...

        # 流式原始字节（用于 SSE 渐进传输）
        async for chunk_b64 in tts.synthesize_stream_bytes("..."):
            ...
    """

    def __init__(self, voice: str = None, rate: str = None):
        self.voice = voice or CONFIG.tts_voice
        self.rate = rate or CONFIG.tts_rate
        self._warmed_up = False

    async def warm_up(self):
        """预热 TTS 连接，减少首次调用延迟"""
        if self._warmed_up:
            return
        try:
            comm = edge_tts.Communicate(text="。", voice=self.voice, rate=self.rate)
            async for _ in comm.stream():
                pass
            self._warmed_up = True
            logger.info("Edge-TTS 预热完成")
        except Exception as e:
            logger.warning(f"Edge-TTS 预热失败（不影响正常使用）: {e}")

    async def synthesize(self, text: str, voice: str = None, rate: str = None) -> str:
        """
        合成单段文本为语音，返回 base64 编码的 mp3。

        返回: base64 字符串，前端可用 data:audio/mp3;base64,xxx 直接播放
        """
        if not text.strip():
            return ""

        communicate = edge_tts.Communicate(
            text=_clean_text_for_tts(text),
            voice=voice or self.voice,
            rate=rate or self.rate,
        )

        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.write(chunk["data"])

        return base64.b64encode(audio_data.getvalue()).decode("utf-8")

    async def synthesize_stream_bytes(self, text: str, voice: str = None, rate: str = None) -> AsyncIterator[str]:
        """
        流式合成：逐音频块 yield base64 编码的数据，不等待整句完成。

        每个 chunk 是独立的 base64 字符串，前端可以逐块拼接或使用 MediaSource 播放。

        yield: base64 编码的原始音频数据块
        """
        if not text.strip():
            return

        communicate = edge_tts.Communicate(
            text=_clean_text_for_tts(text),
            voice=voice or self.voice,
            rate=rate or self.rate,
        )

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield base64.b64encode(chunk["data"]).decode("utf-8")

    async def synthesize_stream(self, text: str, voice: str = None, rate: str = None) -> AsyncIterator[tuple[str, str]]:
        """
        分句合成：按句子切分文本，逐句合成并 yield。

        yield: (sentence_text, audio_base64)
        """
        sentences = self._split_sentences(text)
        for sentence in sentences:
            if not sentence.strip():
                continue
            audio_b64 = await self.synthesize(sentence, voice, rate)
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

        # 先在逗号处找切分点
        for match in _PHRASE_END.finditer(text):
            end = match.end()
            if end >= min_chars:
                return text[:end].strip(), text[end:].strip()

        # 兜底：在第一个句末标点处切分
        for match in _SENTENCE_END.finditer(text):
            end = match.end()
            return text[:end].strip(), text[end:].strip()

        # 无标点：整体返回
        return text, ""


# 模块级单例
tts_service = EdgeTTSService()
