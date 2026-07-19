# -*- coding: utf-8 -*-
'''
@File    :   difyASR.py
@Author  :   一力辉
'''


from ..builder import ASREngines
from ..engineBase import BaseASREngine
import io, base64
from digitalHuman.protocol import AudioMessage, TextMessage, AUDIO_TYPE
from digitalHuman.utils import logger, httpxAsyncClient, wavToMp3

__all__ = ["DifyApiAsr"]


@ASREngines.register("Dify")
class DifyApiAsr(BaseASREngine): 
    async def run(self, input: AudioMessage, **kwargs) -> TextMessage:
        # 参数校验
        paramters = self.checkParameter(**kwargs)
        API_SERVER = paramters["api_server"]
        API_KEY = paramters["api_key"]
        API_USERNAME = paramters["username"]

        if not API_SERVER.startswith("http://") and not API_SERVER.startswith("https://"):
            raise ValueError(f"Dify ASR api_server 未配置或无效: '{API_SERVER}'，请在设置中填入完整的 Dify API 地址（需包含 http:// 或 https://）")

        headers = {
            'Authorization': f'Bearer {API_KEY}'
        }

        payload = {
            'user': API_USERNAME
        }

        if isinstance(input.data, str):
            input.data = base64.b64decode(input.data)
        if input.type == AUDIO_TYPE.WAV:
            input.data = wavToMp3(input.data)
            input.type = AUDIO_TYPE.MP3
        files = {'file': ('file', io.BytesIO(input.data), 'audio/mp3')}
        response = await httpxAsyncClient.post(API_SERVER + "/audio-to-text", headers=headers, files=files, data=payload)
        if response.status_code != 200:
            raise RuntimeError(f"Dify asr api error: {response.status_code}")
        result = response.json()["text"]
        logger.debug(f"[ASR] Engine response: {result}")
        message = TextMessage(data=result)
        return message