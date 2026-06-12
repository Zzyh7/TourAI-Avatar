"""
语音识别 (STT) 服务包。
使用阿里云 DashScope Paraformer 进行语音转文字。
"""
from .dashscope_stt import transcribe

__all__ = ["transcribe"]
