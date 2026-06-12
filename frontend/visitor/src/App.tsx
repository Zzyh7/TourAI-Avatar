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
import AdminPanel from './components/AdminPanel';
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
  const [isAdmin, setIsAdmin] = useState(false);

  const abortRef = useRef<AbortController | null>(null);

  const { enqueue, stop: stopAudio } = useAudioPlayer((text) => {
    setCurrentText(text);
    setIsSpeaking(true);
  });

  // 初始化会话
  useEffect(() => {
    createSession().then(setSessionId);
  }, []);

  // 打断当前生成：中止请求 + 停止音频
  const abortGeneration = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    stopAudio();
    setLoading(false);
    setStreamingText('');
    setIsSpeaking(false);
    setEmotion('neutral');
  }, [stopAudio]);

  // 发送消息（或打断当前）
  const handleSend = useCallback(async (text: string) => {
    if (!text.trim()) return;

    // 如果正在生成，打断当前，开始新问题
    if (loading) {
      abortGeneration();
      // 小延迟让 abort 生效，然后继续发送新问题
      await new Promise(r => setTimeout(r, 50));
    }

    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setStreamingText('');
    setEmotion('thinking');
    setLoading(true);

    // 创建新的 AbortController
    const controller = new AbortController();
    abortRef.current = controller;

    let fullAnswer = '';

    try {
      for await (const event of streamChat(text, sessionId, controller.signal)) {
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
      // AbortError 是用户主动打断，不需要显示错误
      if (err instanceof DOMException && err.name === 'AbortError') {
        return;
      }
      setMessages(prev => [
        ...prev,
        { role: 'system', content: `连接失败：${err.message}` },
      ]);
    } finally {
      setLoading(false);
      if (abortRef.current === controller) {
        abortRef.current = null;
      }
    }
  }, [sessionId, loading, enqueue, abortGeneration]);

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
        <h1 style={styles.title}>{isAdmin ? '⚙️ 景区导览管理后台' : '🏛️ 景区导览AI数字人'}</h1>
        <div style={styles.headerRight}>
          <button
            onClick={() => setIsAdmin(!isAdmin)}
            style={{
              padding: '6px 16px', background: isAdmin ? '#ef5350' : '#1976d2', color: '#fff',
              border: 'none', borderRadius: 6, fontSize: 13, cursor: 'pointer', fontWeight: 500,
            }}
          >
            {isAdmin ? '👤 游客端' : '⚙️ 管理后台'}
          </button>
          {!isAdmin && (
            <>
              <PhotoRecognition disabled={loading} onResult={handlePhotoResult} />
              <VoiceButton onResult={handleVoiceResult} disabled={loading} />
            </>
          )}
        </div>
      </header>

      {isAdmin ? (
        <div style={{ flex: 1, minHeight: 0 }}>
          <AdminPanel />
        </div>
      ) : (
        <>
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
            onStop={abortGeneration}
          />
        </div>
      </div>
        </>
      )}
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
