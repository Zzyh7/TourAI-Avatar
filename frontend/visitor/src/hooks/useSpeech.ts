/**
 * Web Speech API 封装 —— 语音识别 (ASR)
 *
 * 注意：Chrome 的 SpeechRecognition 将音频发送到 Google 服务器进行识别。
 * 在中国大陆可能需要 VPN 才能使用。
 * 如果不可用，请使用服务端 ASR 方案（DashScope 语音识别）。
 */
import { useState, useCallback, useRef } from 'react';

declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

export type SpeechError =
  | 'not-supported'
  | 'no-speech'
  | 'aborted'
  | 'network'
  | 'not-allowed'
  | 'service-not-allowed'
  | 'unknown';

export function useSpeech(onResult: (text: string) => void) {
  const [isListening, setIsListening] = useState(false);
  const [supported, setSupported] = useState(true);
  const [lastError, setLastError] = useState<SpeechError | null>(null);
  const recognitionRef = useRef<any>(null);

  const start = useCallback(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSupported(false);
      setLastError('not-supported');
      console.warn('[ASR] Web Speech API 不可用（浏览器不支持）');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'zh-CN';
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event: any) => {
      const text = event.results[0][0].transcript;
      setLastError(null);
      onResult(text);
      setIsListening(false);
    };

    recognition.onerror = (event: any) => {
      const errorMap: Record<string, SpeechError> = {
        'no-speech': 'no-speech',
        'aborted': 'aborted',
        'network': 'network',
        'not-allowed': 'not-allowed',
        'service-not-allowed': 'service-not-allowed',
      };
      const errType = errorMap[event.error] || 'unknown';
      setLastError(errType);
      setIsListening(false);
      console.warn(`[ASR] 识别失败: ${event.error} (${event.message || ''})`);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;
    setLastError(null);
    try {
      recognition.start();
      setIsListening(true);
    } catch (e: any) {
      console.error('[ASR] 启动失败:', e);
      setIsListening(false);
      setLastError('unknown');
    }
  }, [onResult]);

  const stop = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
    }
  }, []);

  /** 人类可读的错误提示 */
  const errorMessage = (() => {
    switch (lastError) {
      case 'not-supported':
        return '当前浏览器不支持语音识别，请使用 Chrome 或 Edge';
      case 'no-speech':
        return '未检测到语音，请靠近麦克风再试一次';
      case 'aborted':
        return null; // 用户主动停止，不是错误
      case 'network':
        return '语音识别需要访问 Google 服务，但在中国大陆被屏蔽。请使用 VPN 或等待服务端语音识别上线';
      case 'not-allowed':
        return '麦克风权限被拒绝，请在浏览器设置中允许访问麦克风';
      case 'service-not-allowed':
        return '语音识别服务不可用，可能是网络问题';
      case 'unknown':
        return '语音识别失败，请重试';
      default:
        return null;
    }
  })();

  return { isListening, supported, lastError, errorMessage, start, stop };
}
