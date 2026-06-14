/**
 * GPS 触发讲解组件
 *
 * 每5秒轮询 /api/gps/check，当用户进入景点触发范围时：
 *   1. 弹出确认框："我们到了XXX，是否进行讲解？"
 *   2. 用户确认 → 发送景点描述到聊天
 *   3. 用户拒绝 → 标记为已访问，不再触发
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import type { GpsPosition } from '../hooks/useGeolocation';

interface SpotInfo {
  name: string;
  distance_m: number;
  description: string;
  category: string;
  visit_duration: number;
}

interface LocationTriggerProps {
  position: GpsPosition | null;
  onTrigger: (message: string) => void;
  enabled?: boolean;
}

export default function LocationTrigger({ position, onTrigger, enabled = true }: LocationTriggerProps) {
  const [pendingSpot, setPendingSpot] = useState<SpotInfo | null>(null);
  const [showConfirm, setShowConfirm] = useState(false);
  const visitedRef = useRef<Set<string>>(new Set());
  const checkingRef = useRef(false);

  // 轮询 GPS 检测
  const checkTrigger = useCallback(async () => {
    if (!position || checkingRef.current || !enabled) return;
    checkingRef.current = true;

    try {
      const visited = Array.from(visitedRef.current).join(',');
      const url = `/api/gps/check?lat=${position.lat}&lng=${position.lng}&visited=${encodeURIComponent(visited)}`;
      const resp = await fetch(url);
      const data = await resp.json();

      if (data.triggered && data.spot) {
        const spot: SpotInfo = data.spot;
        // 避免重复弹窗
        if (!visitedRef.current.has(spot.name)) {
          setPendingSpot(spot);
          setShowConfirm(true);
        }
      }
    } catch {
      // 静默失败，下次轮询重试
    } finally {
      checkingRef.current = false;
    }
  }, [position, enabled]);

  // 每5秒检测一次
  useEffect(() => {
    if (!position || !enabled) return;
    checkTrigger(); // 立即检测一次
    const timer = setInterval(checkTrigger, 5000);
    return () => clearInterval(timer);
  }, [position, enabled, checkTrigger]);

  // 用户确认讲解
  const handleConfirm = useCallback(() => {
    if (!pendingSpot) return;
    visitedRef.current.add(pendingSpot.name);
    setShowConfirm(false);

    const msg = `我们到了${pendingSpot.name}，请帮我介绍一下这里`;
    onTrigger(msg);
  }, [pendingSpot, onTrigger]);

  // 用户拒绝
  const handleDecline = useCallback(() => {
    if (!pendingSpot) return;
    visitedRef.current.add(pendingSpot.name);
    setShowConfirm(false);
    setPendingSpot(null);
  }, [pendingSpot]);

  if (!showConfirm || !pendingSpot) return null;

  return (
    <div style={s.overlay}>
      <div style={s.card}>
        <div style={s.icon}>📍</div>
        <div style={s.title}>我们到了{pendingSpot.name}</div>
        <div style={s.subtitle}>
          距您约{pendingSpot.distance_m}米 · {pendingSpot.category}
        </div>
        <div style={s.question}>是否进行讲解？</div>
        <div style={s.buttons}>
          <button onClick={handleConfirm} style={s.btnYes}>
            🎧 开始讲解
          </button>
          <button onClick={handleDecline} style={s.btnNo}>
            暂不需要
          </button>
        </div>
      </div>
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'fixed',
    top: 0, left: 0, right: 0, bottom: 0,
    background: 'rgba(0,0,0,0.4)',
    zIndex: 9999,
    display: 'flex',
    alignItems: 'flex-end',
    justifyContent: 'center',
    paddingBottom: 40,
  },
  card: {
    background: '#fff',
    borderRadius: 20,
    padding: '28px 24px 20px',
    maxWidth: 380,
    width: '90%',
    textAlign: 'center',
    boxShadow: '0 12px 40px rgba(0,0,0,0.25)',
    animation: 'slideUp 0.3s ease-out',
  },
  icon: { fontSize: 40, marginBottom: 10 },
  title: { fontSize: 20, fontWeight: 700, color: '#1a1a2e', marginBottom: 4 },
  subtitle: { fontSize: 13, color: '#999', marginBottom: 12 },
  question: { fontSize: 15, color: '#555', marginBottom: 20 },
  buttons: { display: 'flex', gap: 12, justifyContent: 'center' },
  btnYes: {
    flex: 1, padding: '12px 0', borderRadius: 24,
    border: 'none', background: 'linear-gradient(135deg, #667eea, #764ba2)',
    color: '#fff', fontSize: 15, fontWeight: 700, cursor: 'pointer',
    boxShadow: '0 4px 14px rgba(102,126,234,0.35)',
  },
  btnNo: {
    flex: 1, padding: '12px 0', borderRadius: 24,
    border: '1px solid #ddd', background: '#fff',
    color: '#999', fontSize: 14, cursor: 'pointer',
  },
};
