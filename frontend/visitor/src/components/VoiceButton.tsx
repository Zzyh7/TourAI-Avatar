/**
 * 语音输入按钮 —— 点击开始/停止录音。
 * 使用阿里云 DashScope Paraformer 做服务端语音识别（国内可用，无需 VPN）。
 */
import { useAudioRecorder } from '../hooks/useAudioRecorder';

interface VoiceButtonProps {
  onResult: (text: string) => void;
  disabled?: boolean;
}

export default function VoiceButton({ onResult, disabled }: VoiceButtonProps) {
  const { isListening, error, start, stop } = useAudioRecorder(onResult);

  return (
    <div style={{ position: 'relative', display: 'inline-flex' }}>
      <button
        onClick={isListening ? stop : start}
        disabled={disabled}
        style={{
          ...styles.btn,
          background: isListening ? '#f44336' : '#4CAF50',
          animation: isListening ? 'pulse 0.6s ease-in-out infinite' : 'none',
          opacity: disabled ? 0.5 : 1,
        }}
        title={isListening ? '点击停止录音' : '点击开始语音提问'}
      >
        {isListening ? '⏹' : '🎤'}
      </button>

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
    maxWidth: 320,
    whiteSpace: 'normal' as const,
  } as React.CSSProperties,
};
