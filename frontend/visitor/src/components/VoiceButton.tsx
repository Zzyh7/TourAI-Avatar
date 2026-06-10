/**
 * 语音输入按钮 —— 点击开始/停止录音。
 */
import { useSpeech } from '../hooks/useSpeech';

interface VoiceButtonProps {
  onResult: (text: string) => void;
  disabled?: boolean;
}

export default function VoiceButton({ onResult, disabled }: VoiceButtonProps) {
  const { isListening, supported, start, stop } = useSpeech(onResult);

  if (!supported) {
    return (
      <button disabled style={styles.btn} title="浏览器不支持语音识别">
        🎤
      </button>
    );
  }

  return (
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
};
