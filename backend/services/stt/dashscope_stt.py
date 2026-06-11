"""
DashScope 语音识别 (Paraformer / fun-asr-realtime)

前端发送 WAV（16kHz 单声道 16-bit PCM），后端通过 Recognition.call()
完成文件级识别。SDK 版本要求提供 callback（即使同步模式也需要），
使用空回调即可。
"""

import tempfile
import os
import logging
from dashscope.audio.asr import Recognition, RecognitionCallback

logger = logging.getLogger(__name__)

# MIME → DashScope format 映射
MIME_FORMAT_MAP = {
    "audio/wav": "wav",
    "audio/wave": "wav",
    "audio/x-wav": "wav",
    "audio/webm": "opus",
    "audio/ogg": "opus",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/aac": "aac",
    "audio/x-pcm": "pcm",
    "audio/opus": "opus",
    "audio/spex": "speex",
    "audio/amr": "amr",
}


class _NoopCallback(RecognitionCallback):
    """空回调 —— call() 同步阻塞，不触发回调"""
    def on_event(self, result):
        pass


def transcribe(audio_data: bytes, mime_type: str = "audio/wav") -> str:
    """
    将音频数据转为文字。

    参数:
        audio_data: 音频字节数据
        mime_type: 前端传入的 Content-Type

    返回:
        识别出的文字，失败返回空字符串
    """
    fmt = MIME_FORMAT_MAP.get(mime_type, "wav")
    suffix = _format_to_suffix(fmt)

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_data)
            tmp_path = f.name

        recognition = Recognition(
            model="fun-asr-realtime",
            callback=_NoopCallback(),
            format=fmt,
            sample_rate=16000,
        )
        result = recognition.call(tmp_path)

        if result.status_code == 200:
            sentence = result.get_sentence()
            # sentence 可能是 dict 或 list[dict]，取第一个的 text
            if isinstance(sentence, list) and len(sentence) > 0:
                text = sentence[0].get("text", "")
            elif isinstance(sentence, dict):
                text = sentence.get("text", "")
            else:
                text = ""
            logger.info(
                f"ASR: \"{text[:80]}...\"" if len(text) > 80 else f"ASR: \"{text}\""
            )
            return text.strip()
        else:
            logger.error(f"DashScope ASR failed: {result.status_code} {result.message}")
            return ""

    except Exception as e:
        logger.error(f"STT error: {e}")
        return ""

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _format_to_suffix(fmt: str) -> str:
    mapping = {
        "wav": ".wav", "pcm": ".pcm", "mp3": ".mp3",
        "opus": ".opus", "speex": ".spx", "aac": ".aac",
        "amr": ".amr",
    }
    return mapping.get(fmt, ".wav")
