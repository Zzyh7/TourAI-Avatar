"""
Edge-TTS 语音合成 —— 微软免费 TTS 服务，异步调用，支持分句合成。
"""
import asyncio
import io
import base64
import re
from typing import AsyncIterator
import edge_tts
from config import CONFIG


# 中文分句正则
_SENTENCE_END = re.compile(r"[。！？；\n]")


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
    """

    def __init__(self, voice: str = None, rate: str = None):
        self.voice = voice or CONFIG.tts_voice
        self.rate = rate or CONFIG.tts_rate

    async def synthesize(self, text: str, voice: str = None, rate: str = None) -> str:
        """
        合成单段文本为语音，返回 base64 编码的 mp3。

        返回: base64 字符串，前端可用 data:audio/mp3;base64,xxx 直接播放
        """
        if not text.strip():
            return ""

        communicate = edge_tts.Communicate(
            text=text.strip(),
            voice=voice or self.voice,
            rate=rate or self.rate,
        )

        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.write(chunk["data"])

        return base64.b64encode(audio_data.getvalue()).decode("utf-8")

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


# 模块级单例
tts_service = EdgeTTSService()
