/**
 * 语音输入按钮 —— 点击开始/停止录音。
 *
 * 双模式自动切换:
 *   1. 优先使用浏览器内置 Web Speech API (免费、无需 Key、低延迟)
 *   2. 若浏览器不支持或在中国大陆被墙 → 回退到 DashScope 服务端识别
 */
import { useState, useCallback, useEffect } from 'react';
import { useSpeech } from '../hooks/useSpeech';
import { useAudioRecorder } from '../hooks/useAudioRecorder';

interface VoiceButtonProps {
  onResult: (text: string) => void;
  /** 开始录音前调用，用于打断正在进行的 AI 回答 */
  onInterrupt?: () => void;
}

/** 检测 Web Speech API 是否可用（不实际请求权限，只检查 API 存在） */
function checkWebSpeechSupport(): boolean {
  if (typeof window === 'undefined') return false;
  const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
  return !!SR;
}

export default function VoiceButton({ onResult, onInterrupt }: VoiceButtonProps) {
  // 首次渲染时检测浏览器是否支持 Web Speech API
  const [webSpeechAvailable] = useState(() => checkWebSpeechSupport());
  // 当前使用模式: 'web-speech' | 'dashscope'
  const [mode, setMode] = useState<'web-speech' | 'dashscope'>(webSpeechAvailable ? 'web-speech' : 'dashscope');
  // 标记 Web Speech 是否因网络问题不可用（被墙）
  const [webSpeechBlocked, setWebSpeechBlocked] = useState(false);

  // Web Speech API hook
  const webSpeech = useSpeech(onResult);

  // DashScope hook
  const dashScope = useAudioRecorder(onResult);

  // 拦截 Web Speech 的 network / service-not-allowed 错误，自动切换到 DashScope
  useEffect(() => {
    if (mode === 'web-speech' && webSpeech.lastError) {
      if (webSpeech.lastError === 'network' || webSpeech.lastError === 'service-not-allowed') {
        // Web Speech 被墙，静默切换到 DashScope
        console.warn('[Voice] Web Speech API 不可用（网络限制），切换到 DashScope 服务端识别');
        setWebSpeechBlocked(true);
        setMode('dashscope');
      }
    }
  }, [mode, webSpeech.lastError]);

  // 根据当前模式选择对应的 hook
  const isListening = mode === 'web-speech' ? webSpeech.isListening : dashScope.isListening;

  const start = useCallback(() => {
    // 开始录音前先打断正在进行的 AI 回答
    onInterrupt?.();
    if (mode === 'web-speech') {
      webSpeech.start();
    } else {
      dashScope.start();
    }
  }, [mode, webSpeech.start, dashScope.start, onInterrupt]);

  const stop = useCallback(() => {
    if (mode === 'web-speech') {
      webSpeech.stop();
    } else {
      dashScope.stop();
    }
  }, [mode, webSpeech.stop, dashScope.stop]);

  // 合并错误信息
  let error: string | null = null;
  if (mode === 'web-speech') {
    error = webSpeech.errorMessage;
  } else {
    error = dashScope.error;
    // 如果 DashScope 出错且 Web Speech 可用但之前被墙，提示可尝试切换
    if (error && webSpeechAvailable && webSpeechBlocked) {
      error = `${error}（浏览器内置语音识别因网络限制不可用）`;
    }
  }

  // 手动切换到 DashScope 的按钮（仅在 Web Speech 可用但想用服务端时显示）
  const showModeSwitch = webSpeechAvailable && !webSpeechBlocked;

  return (
    <div style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', gap: 8 }}>
      {/* 模式切换小标签 */}
      {showModeSwitch && !isListening && (
        <span
          onClick={() => setMode(mode === 'web-speech' ? 'dashscope' : 'web-speech')}
          style={{
            fontSize: 10,
            color: '#999',
            cursor: 'pointer',
            background: '#f5f5f5',
            padding: '2px 8px',
            borderRadius: 10,
            userSelect: 'none',
          }}
          title={`当前: ${mode === 'web-speech' ? '浏览器语音识别' : 'DashScope 服务端识别'}，点击切换`}
        >
          {mode === 'web-speech' ? '🌐浏览器' : '☁️服务端'}
        </span>
      )}

      <button
        onClick={isListening ? stop : start}
        style={{
          ...styles.btn,
          background: isListening ? '#f44336' : mode === 'web-speech' ? '#4CAF50' : '#1976d2',
          animation: isListening ? 'pulse 0.6s ease-in-out infinite' : 'none',
        }}
        title={
          isListening
            ? '点击停止录音'
            : mode === 'web-speech'
              ? '点击开始语音提问（浏览器识别）'
              : '点击开始语音提问（服务端识别）'
        }
      >
        {isListening ? '⏹' : '🎤'}
      </button>

      {/* 错误提示 */}
      {error && !isListening && (
        <div style={styles.errorTooltip}>
          {error}
        </div>
      )}
    </div>
  );
}

const styles = {
  btn: {
    width: 56,
    height: 56,
    borderRadius: '50%',
    border: 'none',
    color: '#fff',
    fontSize: 24,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 4px 16px rgba(0,0,0,0.2)',
    transition: 'transform 0.2s',
  } as React.CSSProperties,
  errorTooltip: {
    position: 'absolute',
    top: '100%',
    right: 0,
    marginTop: 8,
    padding: '8px 14px',
    background: '#ff5252',
    color: '#fff',
    fontSize: 13,
    borderRadius: 8,
    zIndex: 1000,
    boxShadow: '0 4px 12px rgba(255,82,82,0.4)',
    maxWidth: 360,
    whiteSpace: 'normal' as const,
  } as React.CSSProperties,
};
