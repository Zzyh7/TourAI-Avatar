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

  const abortRef = useRef<AbortController | null>(null);
  // 用 ref 追踪 streamingText，供 abortGeneration 读取最新值
  const streamingTextRef = useRef('');
  // generation 计数器：打断时递增，旧流中的 audio/token 事件会被丢弃，避免语音残留
  const generationRef = useRef(0);

  const { enqueue, stop: stopAudio } = useAudioPlayer((text) => {
    setCurrentText(text);
    setIsSpeaking(true);
  });

  // 初始化会话
  useEffect(() => {
    createSession().then(setSessionId);
  }, []);

  // 同步 streamingText 到 ref
  useEffect(() => {
    streamingTextRef.current = streamingText;
  }, [streamingText]);

  // 打断当前生成：中止请求 + 停止音频，保存部分回复
  const abortGeneration = useCallback((savePartial = true) => {
    // 递增 generation，让旧流中尚未处理的 audio/token 事件全部丢弃
    generationRef.current += 1;
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    stopAudio();
    // 保存已生成的部分回复到聊天记录，避免内容丢失（类似 ChatGPT 的打断行为）
    if (savePartial) {
      const partial = streamingTextRef.current;
      if (partial.trim()) {
        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: partial },
        ]);
      }
    }
    setStreamingText('');
    setIsSpeaking(false);
    setEmotion('neutral');
    setLoading(false);
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

    // 记录当前 generation，流循环中每次检查，被打断后旧事件自动丢弃
    const gen = generationRef.current;

    let fullAnswer = '';
    let lastUiUpdate = 0;  // 节流用：上次UI更新时间戳
    let firstToken = true; // 首个 token 标记，只做一次 emotion 过渡

    try {
      for await (const event of streamChat(text, sessionId, controller.signal)) {
        // 检查 generation：如果被打断（generation 已递增），丢弃旧流剩余事件
        if (generationRef.current !== gen) break;

        switch (event.type) {
          case 'token':
            fullAnswer += event.data.text;
            streamingTextRef.current = fullAnswer;  // ref 始终实时，供打断读取
            // 首个 token：从 thinking 切到 neutral（只做一次）
            if (firstToken) {
              firstToken = false;
              setEmotion('neutral');
            }
            // 节流 UI 更新：最多每 50ms 更新一次，减少重渲染卡顿
            const now = Date.now();
            if (now - lastUiUpdate >= 50) {
              lastUiUpdate = now;
              setStreamingText(fullAnswer);
            }
            break;

          case 'audio':
            if (generationRef.current === gen) {
              enqueue(event.data.base64, event.data.text);
            }
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
            onStop={abortGeneration}
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
