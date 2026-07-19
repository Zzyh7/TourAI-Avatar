/**
 * 聊天面板 —— 文本对话区 + 输入框。
 */
import { useState, useEffect, useRef } from 'react';

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

interface ChatPanelProps {
  messages: Message[];
  onSend: (text: string) => void;
  disabled?: boolean;
  streamingText?: string;
  onStop?: () => void;
}

export default function ChatPanel({ messages, onSend, disabled, streamingText, onStop }: ChatPanelProps) {
  const [input, setInput] = useState('');
  const listRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部 —— 用 scrollTop 直接赋值，比 scrollIntoView 性能好得多
  useEffect(() => {
    const el = listRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages, streamingText]);

  const handleSend = () => {
    const text = input.trim();
    if (!text) return;
    onSend(text);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={styles.container}>
      {/* 消息列表 */}
      <div ref={listRef} style={styles.messageList}>
        {messages.length === 0 && (
          <div style={styles.welcome}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>👋</div>
            <div style={{ fontSize: 16, color: '#666', marginBottom: 4 }}>您好！我是景区导览数字人 <b>小僧</b></div>
            <div style={{ fontSize: 13, color: '#999' }}>
              您可以问我景点历史、文化故事、路线推荐<br />
              也可以点击麦克风按钮语音提问
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              ...styles.message,
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
            }}
          >
            <div style={{
              ...styles.bubble,
              background: msg.role === 'user' ? '#1976D2' : msg.role === 'system' ? '#FFF3E0' : '#F5F5F5',
              color: msg.role === 'user' ? '#fff' : '#333',
              borderTopRightRadius: msg.role === 'user' ? 4 : 18,
              borderTopLeftRadius: msg.role === 'user' ? 18 : 4,
            }}>
              {msg.content}
            </div>
          </div>
        ))}

        {/* 流式输出中的文字 */}
        {streamingText && (
          <div style={{ ...styles.message, justifyContent: 'flex-start' }}>
            <div style={{
              ...styles.bubble,
              background: '#F5F5F5',
              color: '#333',
              borderTopRightRadius: 18,
              borderTopLeftRadius: 4,
            }}>
              {streamingText}
              <span style={styles.cursor}>▌</span>
            </div>
          </div>
        )}
      </div>

      {/* 输入区 */}
      <div style={styles.inputArea}>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入您的问题..."
          style={styles.input}
        />
        {disabled && onStop && (
          <button
            onClick={onStop}
            style={styles.stopBtn}
            title="停止生成"
          >
            ⏹
          </button>
        )}
        <button
          onClick={handleSend}
          disabled={!input.trim()}
          style={{
            ...styles.sendBtn,
            opacity: !input.trim() ? 0.5 : 1,
          }}
        >
          ➤
        </button>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    background: '#fff',
    borderRadius: 12,
    overflow: 'hidden',
    boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
  },
  messageList: {
    flex: 1,
    overflowY: 'auto',
    padding: '16px',
  },
  welcome: {
    textAlign: 'center',
    padding: '40px 20px',
  },
  message: {
    display: 'flex',
    marginBottom: 12,
  },
  bubble: {
    maxWidth: '80%',
    padding: '10px 16px',
    borderRadius: 18,
    fontSize: 14,
    lineHeight: 1.6,
    wordBreak: 'break-word',
  },
  inputArea: {
    display: 'flex',
    padding: '12px 16px',
    borderTop: '1px solid #eee',
    gap: 8,
  },
  input: {
    flex: 1,
    padding: '10px 16px',
    borderRadius: 24,
    border: '1px solid #e0e0e0',
    fontSize: 14,
    outline: 'none',
  },
  sendBtn: {
    width: 44,
    height: 44,
    borderRadius: '50%',
    border: 'none',
    background: '#1976D2',
    color: '#fff',
    fontSize: 18,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  stopBtn: {
    width: 44,
    height: 44,
    borderRadius: '50%',
    border: 'none',
    background: '#ff4d4f',
    color: '#fff',
    fontSize: 18,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    animation: 'pulse 1.5s infinite',
  },
  cursor: {
    animation: 'blink 0.8s infinite',
    color: '#1976D2',
  },
};
