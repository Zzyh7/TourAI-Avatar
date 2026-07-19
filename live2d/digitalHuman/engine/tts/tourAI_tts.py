# -*- coding: utf-8 -*-
'''
@File    :   tourAI_tts.py
@Author  :   TourAI
@Desc    :   豆包 TTS 引擎 —— 通过 TourAI 后端调用火山引擎豆包语音合成
'''

from ..builder import TTSEngines
from ..engineBase import BaseTTSEngine
import aiohttp
import base64
from typing import List
from digitalHuman.protocol import *
from digitalHuman.utils import logger

__all__ = ["TourAITTS"]

# TourAI 豆包 TTS 可用音色（与 backend/services/tts/doubao_tts.py 同步）
DOUBAO_VOICES = [
    VoiceDesc(name="zh_male_shaonianzixin_uranus_bigtts", gender=GENDER_TYPE.MALE),       # 少年自信 (默认)
    VoiceDesc(name="zh_male_tiancaitongsheng_mars_bigtts", gender=GENDER_TYPE.MALE),      # 天才童声 (男)
    VoiceDesc(name="zh_female_vv_uranus_bigtts", gender=GENDER_TYPE.FEMALE),              # Vivi 2.0 女声
    VoiceDesc(name="zh_female_xiaohe_uranus_bigtts", gender=GENDER_TYPE.FEMALE),          # Mindy 女声
    VoiceDesc(name="zh_male_m191_uranus_bigtts", gender=GENDER_TYPE.MALE),                # Kian 男声
    VoiceDesc(name="zh_male_taocheng_uranus_bigtts", gender=GENDER_TYPE.MALE),            # Cedric 男声
    VoiceDesc(name="zh_female_shuangkuaisisi_moon_bigtts", gender=GENDER_TYPE.FEMALE),    # 新闻播报女声
    VoiceDesc(name="zh_male_yuanboxiaoshu_moon_bigtts", gender=GENDER_TYPE.MALE),         # 温暖男主播
]

# TourAI 后端 TTS 接口
TOURAI_TTS_URL = "http://localhost:8000/api/tts"


@TTSEngines.register("TourAITTS")
class TourAITTS(BaseTTSEngine):
    """豆包 TTS 引擎，通过 TourAI 后端代理调用火山引擎豆包语音合成"""

    async def voices(self, **kwargs) -> List[VoiceDesc]:
        return DOUBAO_VOICES

    async def run(self, input: TextMessage, **kwargs) -> AudioMessage:
        # 参数填充
        voice = "zh_male_shaonianzixin_uranus_bigtts"  # 默认：少年自信

        for paramter in self.parameters():
            if paramter.name == "voice":
                voice = paramter.default if paramter.name not in kwargs else kwargs[paramter.name]

        if not input.data or not input.data.strip():
            raise ValueError("TTS input text is empty")

        text = input.data.strip()
        logger.info(f"[TourAITTS] Synthesizing: voice={voice}, text_len={len(text)}")

        payload = {
            "text": text,
            "voice": voice,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    TOURAI_TTS_URL,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"[TourAITTS] HTTP {resp.status}: {error_text[:200]}")
                        raise RuntimeError(f"TourAI TTS failed: HTTP {resp.status}")

                    # TourAI 返回二进制 MP3
                    audio_bytes = await resp.read()
                    if not audio_bytes or len(audio_bytes) < 100:
                        raise RuntimeError("TourAI TTS returned empty audio")

                    logger.info(f"[TourAITTS] Success: {len(audio_bytes)} bytes MP3")

                    message = AudioMessage(
                        data=base64.b64encode(audio_bytes).decode('utf-8'),
                        sampleRate=24000,
                        sampleWidth=2,
                        type=AUDIO_TYPE.MP3,
                    )
                    return message

        except aiohttp.ClientError as e:
            logger.error(f"[TourAITTS] Connection error: {e}")
            raise RuntimeError(f"TourAI TTS connection failed: {e}")
