/**
 * 灵山胜境 — AI景区导览对话式操作系统
 * Layout: TopNav | Left(AI角色+快捷意图) | Center(对话主舞台) | Right(推荐卡片)
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { streamChat, createSession } from './services/api';
import { useAudioPlayer } from './hooks/useAudioPlayer';
import { useGeolocation } from './hooks/useGeolocation';

interface Message { role: 'user'|'assistant'|'system'; content: string; cards?: {title:string;time:string;spots:string[]} }

const QUICK_INTENTS = ['帮我规划路线','推荐必看景点','听九龙灌浴介绍','一日游方案'];
const RECOMMENDATIONS = [
  {icon:'🌄',title:'灵山经典路线',desc:'3小时精华游览',spots:'大佛→梵宫→九龙灌浴'},
  {icon:'🎭',title:'九龙灌浴',desc:'14:00 / 16:30 表演',spots:'音乐喷泉+莲花开合'},
  {icon:'🏛️',title:'梵宫探秘',desc:'佛教艺术殿堂',spots:'木雕·壁画·琉璃'},
  {icon:'📿',title:'祥符禅寺',desc:'千年古刹',spots:'祈福·素斋体验'},
];

export default function App() {
  const [streamingText, setStreamingText] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState('');
  const [loading, setLoading] = useState(false);
  const [gpsEnabled, setGpsEnabled] = useState(false);
  const [aiStatus, setAiStatus] = useState('🟢 正在待命，为您提供导览服务');
  const [inputText, setInputText] = useState('');
  const abortRef = useRef<AbortController|null>(null);
  const streamingTextRef = useRef('');
  const generationRef = useRef(0);
  const msgsEndRef = useRef<HTMLDivElement>(null);

  const { enqueue, stop: stopAudio } = useAudioPlayer(() => {});
  const { position } = useGeolocation({ interval: 5000, enabled: gpsEnabled });

  useEffect(() => { createSession().then(setSessionId); }, []);
  useEffect(() => { streamingTextRef.current = streamingText; }, [streamingText]);
  useEffect(() => { msgsEndRef.current?.scrollIntoView({behavior:'smooth'}); }, [messages, streamingText]);

  const abortGeneration = useCallback((save = true) => {
    generationRef.current += 1;
    abortRef.current?.abort(); abortRef.current = null;
    stopAudio();
    if (save && streamingTextRef.current.trim()) {
      setMessages(p => [...p, {role:'assistant',content:streamingTextRef.current}]);
    }
    setStreamingText(''); setLoading(false);
    setAiStatus('🟢 正在待命');
  }, [stopAudio]);

  const handleSend = useCallback(async (text: string) => {
    if (!text.trim() || loading) return;
    setMessages(p => [...p, {role:'user',content:text}]);
    setStreamingText(''); setLoading(true); setAiStatus('💭 正在为您规划...');
    const controller = new AbortController(); abortRef.current = controller;
    const gen = generationRef.current;
    let full = '';
    try {
      for await (const event of streamChat(text, sessionId, controller.signal)) {
        if (generationRef.current !== gen) break;
        if (event.type === 'token') {
          full += event.data.text;
          streamingTextRef.current = full;
          setStreamingText(full);
        } else if (event.type === 'audio') {
          if (generationRef.current === gen) enqueue(event.data.base64, event.data.text);
        } else if (event.type === 'done') {
          setMessages(p => [...p, {role:'assistant',content:full}]);
          setStreamingText(''); setAiStatus('🟢 正在待命');
        } else if (event.type === 'error') {
          setMessages(p => [...p, {role:'system',content:`抱歉：${event.data.error}`}]);
        }
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') setMessages(p => [...p, {role:'system',content:'连接失败'}]);
    } finally { setLoading(false); abortRef.current = null; }
  }, [sessionId, loading, enqueue]);

  const handleQuickIntent = (intent: string) => {
    setInputText(intent);
    handleSend(intent);
  };

  return (
    <div style={s.app}>
      {/* ===== TOP NAV ===== */}
      <div style={s.topNav}>
        <div style={{display:'flex',alignItems:'center',gap:8}}>
          <img src="/logo.png?v=20260616" alt="灵山" style={{height:36}} />
          <span style={{fontSize:13,fontWeight:600,color:'#C9A24E',letterSpacing:1}}>AI景区导览系统</span>
        </div>
        <div style={{display:'flex',gap:8,alignItems:'center'}}>
          <a href="http://10.40.0.157:8000" style={s.backLink}>← 首页</a>
        </div>
      </div>

      {/* ===== MAIN 3-COLUMN ===== */}
      <div style={s.main}>
        {/* ===== LEFT: RECOMMENDATIONS ===== */}
        <div style={{...s.rightPanel,borderRight:'1px solid rgba(255,255,255,.06)',borderLeft:'none'}}>
          <h4 style={{color:'#C9A24E',fontSize:13,marginBottom:12,letterSpacing:1}}>📌 今日推荐</h4>
          {RECOMMENDATIONS.map((r,i) => (
            <div key={i} style={s.recCard} onClick={()=>{
              const text=`介绍一下${r.title}`;
              // 调 TourAI 对话 API
              fetch('http://10.40.0.157:8000/api/chat', {
                method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({text, session_id:'rec_'+Date.now()})
              });
              // 通过 postMessage 发送到 Live2D iframe
              const iframe = document.querySelector('iframe') as HTMLIFrameElement;
              if (iframe?.contentWindow) {
                iframe.contentWindow.postMessage({type:'chat',text}, 'http://10.40.0.157:3000');
              }
            }}>
              <div style={{fontSize:24}}>{r.icon}</div>
              <div style={{flex:1}}>
                <div style={{fontSize:13,fontWeight:600,color:'#fff'}}>{r.title}</div>
                <div style={{fontSize:11,color:'rgba(255,255,255,.4)',margin:'2px 0'}}>{r.desc}</div>
                <div style={{fontSize:11,color:'#C9A24E'}}>{r.spots}</div>
              </div>
            </div>
          ))}
          {/* 游览偏好 */}
          <h4 style={{color:'#C9A24E',fontSize:13,marginTop:8,letterSpacing:1}}>🧭 游览偏好</h4>
          {['👨‍👩‍👧 家庭游','🏛️ 文化深度游','🌿 休闲游','📿 祈福游'].map(tag=>(
            <div key={tag} style={{...s.recCard,padding:'8px 12px'}}
              onClick={()=>{
                const text=`我对${tag.replace(/[^一-龥]/g,'')}感兴趣，请推荐适合的路线和讲解重点`;
                fetch('http://10.40.0.157:8000/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,session_id:'pref_'+Date.now()})});
                const iframe=document.querySelector('iframe') as HTMLIFrameElement;
                if(iframe?.contentWindow){iframe.contentWindow.postMessage({type:'chat',text},'http://10.40.0.157:3000')}
              }}>
              <span style={{fontSize:13,color:'rgba(255,255,255,.7)'}}>{tag}</span>
            </div>
          ))}
          {/* GPS 定位 */}
          <div onClick={() => setGpsEnabled(!gpsEnabled)}
            style={{marginTop:8,padding:'14px 16px',borderRadius:12,
              background:gpsEnabled?'linear-gradient(135deg,#4DA3FF,#2563EB)':'rgba(255,255,255,.04)',
              border:gpsEnabled?'none':'1px solid rgba(255,255,255,.08)',
              color:gpsEnabled?'#fff':'rgba(255,255,255,.5)',
              cursor:'pointer',textAlign:'center',fontSize:14,fontWeight:600,transition:'.3s'}}>
            📍 {gpsEnabled?'GPS 功能已开启':'开启 GPS 功能'}
          </div>
        </div>

        {/* ===== CENTER: LIVE2D CHARACTER ===== */}
        <div style={s.centerPanel}>
          <iframe src="http://10.40.0.157:3000/sentio" allow="camera;microphone;autoplay"
            style={{width:'100%',height:'100%',border:'none'}} />
        </div>
      </div>
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  app:{width:'100vw',height:'100vh',background:'#0B0D10',color:'#fff',display:'flex',flexDirection:'column',fontFamily:"'SimSun','STSong','Songti SC',serif",overflow:'hidden'},
  topNav:{display:'flex',alignItems:'center',justifyContent:'space-between',padding:'10px 24px',background:'rgba(11,13,16,.9)',backdropFilter:'blur(14px)',borderBottom:'1px solid rgba(255,255,255,.06)',zIndex:10},
  navBtn:{padding:'5px 12px',borderRadius:12,border:'none',background:'transparent',color:'rgba(255,255,255,.5)',fontSize:12,cursor:'pointer',fontFamily:'inherit'},
  backLink:{fontSize:12,color:'rgba(255,255,255,.4)',textDecoration:'none'},
  main:{flex:1,display:'flex',minHeight:0},
  leftPanel:{width:260,display:'flex',flexDirection:'column',padding:16,gap:12,borderRight:'1px solid rgba(255,255,255,.06)'},
  aiCharWrap:{width:'100%',aspectRatio:'1',borderRadius:16,overflow:'hidden',background:'radial-gradient(ellipse at center, #1a1f2a 0%, #0B0D10 100%)',border:'1px solid rgba(255,255,255,.06)'},
  aiStatus:{padding:'8px 12px',borderRadius:10,background:'rgba(255,255,255,.04)',fontSize:11,color:'rgba(255,255,255,.5)',textAlign:'center'},
  quickIntents:{display:'flex',flexDirection:'column',gap:6},
  intentBtn:{padding:'10px 14px',borderRadius:10,border:'1px solid rgba(255,255,255,.08)',background:'rgba(255,255,255,.03)',color:'rgba(255,255,255,.6)',fontSize:12,cursor:'pointer',textAlign:'left',fontFamily:'inherit',transition:'.2s'},
  centerPanel:{flex:1,display:'flex',flexDirection:'column',minWidth:0},
  chatArea:{flex:1,overflowY:'auto',padding:'20px 24px',display:'flex',flexDirection:'column',gap:10},
  welcomeMsg:{padding:'20px',borderRadius:14,background:'rgba(255,255,255,.03)',border:'1px solid rgba(255,255,255,.04)',marginBottom:8},
  msgBubble:{maxWidth:'80%',padding:'12px 16px',borderRadius:14,fontSize:13,lineHeight:1.7,wordBreak:'break-word'},
  inputRow:{display:'flex',gap:8,padding:'12px 20px',borderTop:'1px solid rgba(255,255,255,.06)'},
  chatInput:{flex:1,padding:'12px 18px',borderRadius:22,border:'1px solid rgba(255,255,255,.1)',background:'rgba(255,255,255,.04)',color:'#fff',fontSize:13,outline:'none',fontFamily:'inherit'},
  sendBtn:{width:40,height:40,borderRadius:'50%',border:'none',background:'linear-gradient(135deg,#C9A24E,#8B5E34)',color:'#fff',fontSize:16,cursor:'pointer'},
  rightPanel:{width:280,padding:16,borderLeft:'1px solid rgba(255,255,255,.06)',display:'flex',flexDirection:'column',gap:10,overflowY:'auto'},
  recCard:{display:'flex',gap:10,padding:12,borderRadius:12,background:'rgba(255,255,255,.03)',border:'1px solid rgba(255,255,255,.05)',cursor:'pointer',transition:'.2s',alignItems:'center'},
};
