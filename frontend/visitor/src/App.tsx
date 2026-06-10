/**
 * 景区导览AI数字人 — 游客端主应用。
 *
 * 布局:
 * ┌─────────────────┬──────────────────┐
 * │   数字人区域     │   聊天面板        │
 * │   (Live2D)      │   (对话+输入)     │
 * │                 │                  │
 * ├─────────────────┴──────────────────┤
 * │  推荐标签栏 + 拍照按钮              │
 * └────────────────────────────────────┘
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import DigitalHuman from './components/DigitalHuman';
import ChatPanel from './components/ChatPanel';
import VoiceButton from './components/VoiceButton';
import RecommendationBar from './components/RecommendationBar';
import PhotoRecognition from './components/PhotoRecognition';
import { useAudioPlayer } from './hooks/useAudioPlayer';
import { streamChat, createSession } from './services/api';

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingText, setStreamingText] = useState('');
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [currentText, setCurrentText] = useState('');
  const [emotion, setEmotion] = useState<'neutral' | 'happy' | 'thinking'>('neutral');
  const [sessionId, setSessionId] = useState('');
  const [selectedTag, setSelectedTag] = useState('');
  const [loading, setLoading] = useState(false);

  const { enqueue, stop } = useAudioPlayer((text) => {
    setCurrentText(text);
    setIsSpeaking(true);
  });

  // 初始化会话
  useEffect(() => {
    createSession().then(setSessionId);
  }, []);

  // 发送消息
  const handleSend = useCallback(async (text: string) => {
    if (!text.trim() || loading) return;

    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setStreamingText('');
    setEmotion('thinking');
    setLoading(true);

    let fullAnswer = '';

    try {
      for await (const event of streamChat(text, sessionId)) {
        switch (event.type) {
          case 'token':
            fullAnswer += event.data.text;
            setStreamingText(fullAnswer);
            setEmotion('neutral');
            break;

          case 'audio':
            enqueue(event.data.base64, event.data.text);
            break;

          case 'tool':
            // 工具调用状态可在状态栏显示
            break;

          case 'done':
            setMessages(prev => [
              ...prev,
              { role: 'assistant', content: fullAnswer },
            ]);
            setStreamingText('');
            setEmotion('happy');
            setIsSpeaking(false);
            break;

          case 'error':
            setMessages(prev => [
              ...prev,
              { role: 'system', content: `抱歉，出了点问题：${event.data.error}` },
            ]);
            setStreamingText('');
            setEmotion('neutral');
            break;
        }
      }
    } catch (err: any) {
      setMessages(prev => [
        ...prev,
        { role: 'system', content: `连接失败：${err.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  }, [sessionId, loading, enqueue]);

  // 语音识别结果
  const handleVoiceResult = useCallback((text: string) => {
    if (text.trim()) {
      handleSend(text);
    }
  }, [handleSend]);

  // 拍照识景结果
  const handlePhotoResult = useCallback((description: string) => {
    setMessages(prev => [
      ...prev,
      { role: 'user', content: '📷 [拍照识景]' },
      { role: 'assistant', content: description },
    ]);
  }, []);

  // 标签切换
  const handleTagSelect = useCallback((tag: string) => {
    setSelectedTag(tag);
    if (tag) {
      handleSend(`我对${tag}感兴趣，请推荐适合的路线和讲解重点`);
    }
  }, [handleSend]);

  return (
    <div style={styles.app}>
      {/* 标题栏 */}
      <header style={styles.header}>
        <h1 style={styles.title}>🏛️ 景区导览AI数字人</h1>
        <div style={styles.headerRight}>
          <PhotoRecognition disabled={loading} onResult={handlePhotoResult} />
          <VoiceButton onResult={handleVoiceResult} disabled={loading} />
        </div>
      </header>

      {/* 推荐标签 */}
      <RecommendationBar onSelect={handleTagSelect} selected={selectedTag} />

      {/* 主区域 */}
      <div style={styles.main}>
        {/* 左侧：数字人 */}
        <div style={styles.leftPanel}>
          <DigitalHuman
            isSpeaking={isSpeaking}
            currentText={currentText}
            emotion={emotion}
          />
        </div>

        {/* 右侧：聊天面板 */}
        <div style={styles.rightPanel}>
          <ChatPanel
            messages={messages}
            onSend={handleSend}
            disabled={loading}
            streamingText={streamingText}
          />
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  app: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    background: 'linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%)',
    fontFamily: "'PingFang SC', 'Microsoft YaHei', sans-serif",
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 24px',
    background: '#fff',
    borderBottom: '1px solid #e8e8e8',
  },
  title: {
    fontSize: 20,
    fontWeight: 700,
    color: '#333',
    margin: 0,
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
  },
  main: {
    display: 'flex',
    flex: 1,
    gap: 16,
    padding: '16px 24px',
    minHeight: 0,
  },
  leftPanel: {
    width: '40%',
    minWidth: 300,
    display: 'flex',
  },
  rightPanel: {
    flex: 1,
    minWidth: 400,
    display: 'flex',
  },
};
