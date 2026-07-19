# -*- coding: utf-8 -*-
'''
@File    :   tourAI_stt.py
@Author  :   TourAI
@Desc    :   TourAI STT 引擎 —— 通过 TourAI 后端调用 DashScope Paraformer 语音识别
'''

from ..builder import ASREngines
from ..engineBase import BaseASREngine
import aiohttp
import base64
from digitalHuman.protocol import AudioMessage, TextMessage, AUDIO_TYPE
from digitalHuman.utils import logger

__all__ = ["TourAISTT"]

TOURAI_STT_URL = "http://localhost:8001/api/stt"


@ASREngines.register("TourAISTT")
class TourAISTT(BaseASREngine):
    """DashScope Paraformer STT 引擎，通过 TourAI 后端代理调用"""

    async def run(self, input: AudioMessage, **kwargs) -> TextMessage:
        if isinstance(input.data, str):
            audio_bytes = base64.b64decode(input.data)
        else:
            audio_bytes = input.data

        if not audio_bytes or len(audio_bytes) < 100:
            raise ValueError("STT audio data is empty")

        logger.info(f"[TourAISTT] Sending audio: {len(audio_bytes)} bytes, type={input.type}")

        # Map Live2D audio type to MIME
        mime_map = {
            AUDIO_TYPE.WAV: "audio/wav",
            AUDIO_TYPE.MP3: "audio/mp3",
        }
        mime_type = mime_map.get(input.type, "audio/mp3")

        try:
            async with aiohttp.ClientSession() as session:
                form = aiohttp.FormData()
                form.add_field("audio", audio_bytes, filename="recording.wav",
                               content_type=mime_type)
                form.add_field("mime_type", mime_type)

                async with session.post(
                    TOURAI_STT_URL,
                    data=form,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"[TourAISTT] HTTP {resp.status}: {error_text[:200]}")
                        raise RuntimeError(f"TourAI STT failed: HTTP {resp.status}")

                    result = await resp.json()
                    logger.info(f"[TourAISTT] Result: success={result.get('success')}, text_len={len(result.get('text', ''))}")

                    if result.get("success"):
                        return TextMessage(data=result["text"])
                    else:
                        raise RuntimeError(result.get("error", "STT recognition failed"))

        except aiohttp.ClientError as e:
            logger.error(f"[TourAISTT] Connection error: {e}")
            raise RuntimeError(f"TourAI STT connection failed: {e}")
