/**
 * 灵山胜境 — AI景区导览对话式操作系统
 * Layout: TopNav | Left(AI角色+快捷意图) | Center(对话主舞台) | Right(推荐卡片)
 */
import { useState, useEffect, useCallback, useRef } from 'react';
const API_BASE = '/api';
import { streamChat, createSession } from './services/api';
import { useAudioPlayer } from './hooks/useAudioPlayer';
import { useGeolocation } from './hooks/useGeolocation';

interface Message { role: 'user'|'assistant'|'system'; content: string; cards?: {title:string;time:string;spots:string[]} }

const QUICK_INTENTS = ['帮我规划路线','推荐必看景点','听九龙灌浴介绍','一日游方案'];
const RECOMMENDATIONS = [
  {icon:'🌄',title:'灵山经典路线',desc:'3小时精华游览',spots:'大佛→梵宫→九龙灌浴'},
  {icon:'/jiulong.png',title:'九龙灌浴',desc:'14:00 / 16:30 表演',spots:'音乐喷泉+莲花开合'},
  {icon:'/fangong.png',title:'梵宫探秘',desc:'佛教艺术殿堂',spots:'木雕·壁画·琉璃'},
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
  const dhIframeRef = useRef<HTMLIFrameElement>(null);

  const { enqueue, stop: stopAudio } = useAudioPlayer(() => {});
  const { position } = useGeolocation({ interval: 5000, enabled: gpsEnabled });

  useEffect(() => { createSession().then(setSessionId); }, []);
  useEffect(() => { streamingTextRef.current = streamingText; }, [streamingText]);
  useEffect(() => { msgsEndRef.current?.scrollIntoView({behavior:'smooth'}); }, [messages, streamingText]);

  // 拉取管理后台音色配置，传给 Live2D 数字人 iframe
  useEffect(() => {
    const sendConfig = () => {
      fetch(`${API_BASE}/public-config`)
        .then(r => r.json())
        .then(cfg => {
          const iframe = dhIframeRef.current;
          if (iframe?.contentWindow) {
            iframe.contentWindow.postMessage(
              { type: 'config', voice: cfg.voice, character: cfg.character },
              '*'
            );
          }
        })
        .catch(() => {});
    };
    // 立即发送一次
    sendConfig();
    // iframe 加载完成后补发一次
    const iframe = dhIframeRef.current;
    iframe?.addEventListener('load', sendConfig);
    return () => { iframe?.removeEventListener('load', sendConfig); };
  }, []);

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
          <span style={{fontSize:13,fontWeight:600,color:'#B8860B',letterSpacing:1}}>AI景区导览系统</span>
        </div>
        <div style={{display:'flex',gap:8,alignItems:'center'}}>
          <a href="http://localhost:8000/" style={s.backLink}>← 首页</a>
        </div>
      </div>

      {/* ===== MAIN 3-COLUMN ===== */}
      <div style={s.main}>
        {/* ===== LEFT: RECOMMENDATIONS ===== */}
        <div style={{...s.rightPanel,borderRight:'1px solid #E0D3C0',borderLeft:'none',overflowY:'visible'}}>
          <h4 style={{color:'#B8860B',fontSize:15,marginBottom:12,letterSpacing:1,textAlign:'center'}}>今日推荐</h4>
          {RECOMMENDATIONS.map((r,i) => (
            <div key={i} style={s.recCard} onClick={()=>{
              const text=`介绍一下${r.title}`;
              // 调 TourAI 对话 API
              fetch(`${API_BASE}/chat`, {
                method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({text, session_id:'rec_'+Date.now()})
              });
              // 通过 postMessage 发送到 Live2D iframe
              const iframe = document.querySelector('iframe') as HTMLIFrameElement;
              if (iframe?.contentWindow) {
                iframe.contentWindow.postMessage({type:'chat',text}, '*');
              }
            }}>
              {r.icon.endsWith('.png') ? <img src={r.icon} alt="" style={{width:40,height:40,borderRadius:8}} /> : <div style={{fontSize:24}}>{r.icon}</div>}
              <div style={{flex:1}}>
                <div style={{fontSize:13,fontWeight:600,color:'#4A3028'}}>{r.title}</div>
                <div style={{fontSize:11,color:'#8B7355',margin:'2px 0'}}>{r.desc}</div>
                <div style={{fontSize:11,color:'#B8860B'}}>{r.spots}</div>
              </div>
            </div>
          ))}
          {/* 游览偏好 */}
          <h4 style={{color:'#B8860B',fontSize:15,marginTop:8,letterSpacing:1,textAlign:'center'}}>游览偏好</h4>
          {['家庭游','文化深度游','休闲游','祈福游'].map(tag=>(
            <div key={tag} style={{...s.recCard,padding:'8px 12px'}}
              onClick={()=>{
                const text=`我对${tag.replace(/[^一-龥]/g,'')}感兴趣，请推荐适合的路线和讲解重点`;
                fetch(`${API_BASE}/chat`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,session_id:'pref_'+Date.now()})});
                const iframe=document.querySelector('iframe') as HTMLIFrameElement;
                if(iframe?.contentWindow){iframe.contentWindow.postMessage({type:'chat',text},'*')}
              }}>
              <span style={{fontSize:13,fontWeight:600,color:'#4A3028'}}>{tag}</span>
            </div>
          ))}
          {/* GPS 定位 */}
          <div onClick={() => setGpsEnabled(!gpsEnabled)}
            style={{marginTop:8,padding:'14px 16px',borderRadius:12,
              background:gpsEnabled?'linear-gradient(135deg,#C9A24E,#8B6914)':'#FFF9ED',
              border:gpsEnabled?'none':'1px solid #E0D3C0',
              color:gpsEnabled?'#fff':'#8B7355',
              cursor:'pointer',textAlign:'center',fontSize:14,fontWeight:600,transition:'.3s'}}>
            📍 {gpsEnabled?'GPS 功能已开启':'开启 GPS 功能'}
          </div>
          {/* 手机体验提示 */}
          <div style={{
            marginTop: 'auto', paddingTop: 16, textAlign: 'center',
            fontSize: 12, color: '#B8860B', letterSpacing: 1, lineHeight: 1.6,
          }}>
            <img src="/qrcode.png" alt="手机扫码体验" style={{
              width: 140, height: 140, borderRadius: 10,
              border: '1px solid #E0D3C0', marginBottom: 10,
            }} />
            <div>扫描上方二维码</div>
            <div>即可在手机上体验</div>
          </div>
        </div>

        {/* ===== CENTER: LIVE2D CHARACTER ===== */}
        <div style={s.centerPanel}>
          <iframe ref={dhIframeRef} src="http://localhost:3000/sentio" allow="camera;microphone;autoplay"
            // Live2D 数字人服务 (live2d/web Next.js, 端口 3000)
            style={{width:'100%',height:'100%',border:'none'}} />
        </div>
      </div>
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  app:{width:'100vw',height:'100vh',background:'#FFFDF5',color:'#4A3028',display:'flex',flexDirection:'column',fontFamily:"'SimSun','STSong','Songti SC',serif",overflow:'hidden'},
  topNav:{display:'flex',alignItems:'center',justifyContent:'space-between',padding:'18px 48px',minHeight:64,background:'rgba(255,253,245,.92)',backdropFilter:'blur(14px)',borderBottom:'1px solid #E0D3C0',zIndex:10},
  navBtn:{padding:'5px 12px',borderRadius:12,border:'none',background:'transparent',color:'#8B7355',fontSize:12,cursor:'pointer',fontFamily:'inherit'},
  backLink:{fontSize:12,color:'#8B7355',textDecoration:'none'},
  main:{flex:1,display:'flex',minHeight:0},
  leftPanel:{width:260,display:'flex',flexDirection:'column',padding:16,gap:12,borderRight:'1px solid #E0D3C0'},
  aiCharWrap:{width:'100%',aspectRatio:'1',borderRadius:16,overflow:'hidden',background:'linear-gradient(135deg, #FFF9ED 0%, #FFF5E0 100%)',border:'1px solid #E0D3C0'},
  aiStatus:{padding:'8px 12px',borderRadius:10,background:'#FFF9ED',fontSize:11,color:'#8B7355',textAlign:'center'},
  quickIntents:{display:'flex',flexDirection:'column',gap:6},
  intentBtn:{padding:'10px 14px',borderRadius:10,border:'1px solid #E0D3C0',background:'#FFF9ED',color:'#4A3028',fontSize:12,cursor:'pointer',textAlign:'left',fontFamily:'inherit',transition:'.2s'},
  centerPanel:{flex:1,display:'flex',flexDirection:'column',minWidth:0},
  chatArea:{flex:1,overflowY:'auto',padding:'20px 24px',display:'flex',flexDirection:'column',gap:10},
  welcomeMsg:{padding:'20px',borderRadius:14,background:'#FFF9ED',border:'1px solid #E0D3C0',marginBottom:8},
  msgBubble:{maxWidth:'80%',padding:'12px 16px',borderRadius:14,fontSize:13,lineHeight:1.7,wordBreak:'break-word'},
  inputRow:{display:'flex',gap:8,padding:'12px 20px',borderTop:'1px solid #E0D3C0'},
  chatInput:{flex:1,padding:'12px 18px',borderRadius:22,border:'1px solid #E0D3C0',background:'#FFF9ED',color:'#4A3028',fontSize:13,outline:'none',fontFamily:'inherit'},
  sendBtn:{width:40,height:40,borderRadius:'50%',border:'none',background:'linear-gradient(135deg,#C9A24E,#8B6914)',color:'#fff',fontSize:16,cursor:'pointer'},
  rightPanel:{width:280,padding:16,borderLeft:'1px solid #E0D3C0',display:'flex',flexDirection:'column',gap:10,overflowY:'auto'},
  recCard:{display:'flex',gap:10,padding:12,borderRadius:12,background:'#FFF9ED',border:'1px solid #E0D3C0',cursor:'pointer',transition:'.2s',alignItems:'center'},
};
