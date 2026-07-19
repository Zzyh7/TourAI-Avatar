# -*- coding: utf-8 -*-
'''
@File    :   dashscopeASR.py
@Author  :   TourAI
'''

import os
import tempfile
import base64
from ..builder import ASREngines
from ..engineBase import BaseASREngine
from digitalHuman.protocol import AudioMessage, TextMessage, AUDIO_TYPE
from digitalHuman.utils import logger

__all__ = ["DashScopeApiAsr"]


@ASREngines.register("DashScope")
class DashScopeApiAsr(BaseASREngine):
    def setup(self):
        pass

    async def run(self, input: AudioMessage, **kwargs) -> TextMessage:
        from dashscope.audio.asr import Recognition, RecognitionCallback

        # 参数校验
        paramters = self.checkParameter(**kwargs)
        API_KEY = paramters.get("api_key", "") or os.getenv("DASHSCOPE_API_KEY", "")

        if not API_KEY or API_KEY.startswith("sk-your-"):
            raise ValueError(
                "DashScope API Key 未配置，请在设置中填入或设置环境变量 DASHSCOPE_API_KEY"
            )

        # 解码音频数据
        audio_bytes: bytes
        if isinstance(input.data, str):
            audio_bytes = base64.b64decode(input.data)
        else:
            audio_bytes = input.data

        if len(audio_bytes) < 100:
            raise ValueError("音频数据为空，请重新录制")

        # 写入临时文件
        suffix = ".wav" if input.type == AUDIO_TYPE.WAV else ".mp3"
        fmt = "wav" if input.type == AUDIO_TYPE.WAV else "mp3"

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                f.write(audio_bytes)
                tmp_path = f.name

            class _NoopCallback(RecognitionCallback):
                def on_event(self, result):
                    pass

            recognition = Recognition(
                model="fun-asr-realtime",
                callback=_NoopCallback(),
                format=fmt,
                sample_rate=input.sampleRate,
                api_key=API_KEY,
            )
            result = recognition.call(tmp_path)

            if result.status_code == 200:
                sentence = result.get_sentence()
                if isinstance(sentence, list) and len(sentence) > 0:
                    text = sentence[0].get("text", "")
                elif isinstance(sentence, dict):
                    text = sentence.get("text", "")
                else:
                    text = ""
                text = text.strip()
                logger.info(f"[ASR] DashScope result: '{text[:60]}...'" if len(text) > 60 else f"[ASR] DashScope result: '{text}'")
                return TextMessage(data=text)
            else:
                raise RuntimeError(
                    f"DashScope ASR 返回错误 (code={result.status_code}): {result.message}"
                )

        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
