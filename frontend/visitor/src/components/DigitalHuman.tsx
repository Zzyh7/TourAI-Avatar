/**
 * Live2D 数字人渲染容器。
 *
 * 简化版实现 —— 使用 Canvas 绘制一个基础动画角色 + 口型指示器。
 * 完整版应集成 Live2D Cubism SDK + oLipsync 插件。
 *
 * 当前实现提供:
 *   - 基础角色展示（CSS 动画 + emoji 角色）
 *   - 说话状态动画（口型脉冲）
 *   - 空闲状态呼吸动画
 *
 * 改造为真实 Live2D 时替换此组件即可，接口保持不变。
 */
import { useState, useEffect, memo } from 'react';

interface DigitalHumanProps {
  isSpeaking: boolean;
  currentText: string;
  emotion?: 'neutral' | 'happy' | 'thinking';
  onStop?: () => void;
}

export default memo(function DigitalHuman({ isSpeaking, currentText, emotion = 'neutral', onStop }: DigitalHumanProps) {
  const [mouthPhase, setMouthPhase] = useState(0);

  // 说话时口型循环动画
  useEffect(() => {
    if (!isSpeaking) {
      setMouthPhase(0);
      return;
    }
    const interval = setInterval(() => {
      setMouthPhase(p => (p + 1) % 4);
    }, 120);
    return () => clearInterval(interval);
  }, [isSpeaking]);

  const emotionEmoji = {
    neutral: '😊',
    happy: '😄',
    thinking: '🤔',
  };

  const mouthShapes = ['─', '△', '○', '□'];
  const eyeShapes = {
    neutral: '◉',
    happy: '^',
    thinking: '◔',
  };

  return (
    <div style={styles.container}>
      {/* Live2D Canvas 占位 — 实际集成时在此挂载 Cubism SDK */}
      <div style={styles.character}>
        <div style={{
          ...styles.face,
          animation: isSpeaking ? 'none' : 'breathe 3s ease-in-out infinite',
        }}>
          {/* 眼睛 */}
          <div style={styles.eyes}>
            <span style={styles.eye}>{eyeShapes[emotion]}</span>
            <span style={{ ...styles.eye, marginLeft: 24 }}>{eyeShapes[emotion]}</span>
          </div>

          {/* 表情 emoji */}
          <div style={styles.emoji}>
            {emotionEmoji[emotion]}
          </div>

          {/* 嘴巴 — 说话时动态变化 */}
          <div style={{
            ...styles.mouth,
            transform: isSpeaking ? `scaleY(${0.4 + mouthPhase * 0.2})` : 'scaleY(1)',
          }}>
            {isSpeaking ? mouthShapes[mouthPhase] : '─'}
          </div>
        </div>
      </div>

      {/* 说话文字提示 */}
      {isSpeaking && currentText && (
        <div style={styles.speechBubble}>
          {currentText.length > 30 ? currentText.slice(0, 30) + '...' : currentText}
        </div>
      )}

      {/* 强制停止按钮 —— 讲解中显示 */}
      {isSpeaking && onStop && (
        <button onClick={onStop} style={styles.stopBtn} title="强制停止讲解">
          ⏹ 停止讲解
        </button>
      )}

      {/* 状态指示 */}
      <div style={{
        ...styles.status,
        background: isSpeaking ? '#C9A24E' : '#8B7355',
        animation: isSpeaking ? 'pulse 0.5s ease-in-out infinite' : 'none',
      }}>
        {isSpeaking ? '🔊 讲解中' : '😊 在线'}
      </div>

      <style>{`
        @keyframes breathe {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.03); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.6; }
        }
      `}</style>
    </div>
  );
});

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    background: 'linear-gradient(180deg, #FFF9ED 0%, #FFF5E0 100%)',
    borderRadius: 20,
    padding: 20,
    position: 'relative',
  },
  character: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 220,
    height: 220,
    background: 'linear-gradient(135deg, #C9A24E 0%, #8B6914 100%)',
    borderRadius: '50%',
    boxShadow: '0 8px 32px rgba(184,134,11,0.3)',
  },
  face: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
  },
  eyes: {
    display: 'flex',
    justifyContent: 'center',
    marginBottom: 8,
  },
  eye: {
    fontSize: 28,
    color: '#fff',
    lineHeight: 1,
  },
  emoji: {
    fontSize: 42,
    lineHeight: 1,
    marginBottom: 8,
  },
  mouth: {
    fontSize: 22,
    color: '#fff',
    fontWeight: 'bold',
    lineHeight: 1,
    transition: 'transform 0.1s',
  },
  speechBubble: {
    position: 'absolute',
    top: 10,
    left: '50%',
    transform: 'translateX(-50%)',
    background: 'rgba(255,255,255,0.95)',
    borderRadius: 12,
    padding: '8px 16px',
    fontSize: 14,
    color: '#333',
    boxShadow: '0 2px 12px rgba(0,0,0,0.1)',
    maxWidth: '90%',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  status: {
    marginTop: 16,
    padding: '4px 16px',
    borderRadius: 20,
    color: '#fff',
    fontSize: 13,
    fontWeight: 600,
  },
  stopBtn: {
    marginTop: 14,
    padding: '8px 24px',
    borderRadius: 24,
    border: 'none',
    background: 'linear-gradient(135deg, #ff4d4f 0%, #ff7875 100%)',
    color: '#fff',
    fontSize: 15,
    fontWeight: 700,
    cursor: 'pointer',
    boxShadow: '0 4px 16px rgba(255,77,79,0.45)',
    animation: 'pulse 1.5s ease-in-out infinite',
    letterSpacing: 1,
  } as React.CSSProperties,
};
