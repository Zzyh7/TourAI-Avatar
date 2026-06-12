/**
 * 游客分层分析 —— 新客/回头客 + 标签 + 偏好分布
 */
import { useState, useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { fetchVisitorSegmentation, type VisitorSegmentationRes } from '../services/api';

export default function VisitorSegmentation() {
  const [data, setData] = useState<VisitorSegmentationRes | null>(null);
  const [loading, setLoading] = useState(true);
  const tagPieRef = useRef<HTMLDivElement>(null);
  const prefPieRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchVisitorSegmentation()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!tagPieRef.current || !data?.tag_distribution) return;
    const c = echarts.init(tagPieRef.current);
    c.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c}人 ({d}%)' },
      legend: { bottom: 0, textStyle: { fontSize: 11 } },
      series: [{
        type: 'pie', radius: ['50%', '70%'], center: ['50%', '43%'],
        data: data.tag_distribution.map(t => ({ value: t.value, name: t.name })),
      }],
    }, true);
    const onResize = () => c.resize();
    window.addEventListener('resize', onResize);
    return () => { window.removeEventListener('resize', onResize); c.dispose(); };
  }, [data]);

  useEffect(() => {
    if (!prefPieRef.current || !data?.preference_distribution) return;
    const c = echarts.init(prefPieRef.current);
    c.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c}人 ({d}%)' },
      legend: { bottom: 0, textStyle: { fontSize: 11 } },
      series: [{
        type: 'pie', radius: ['50%', '70%'], center: ['50%', '43%'],
        data: data.preference_distribution.map(p => ({ value: p.value, name: p.name })),
      }],
    }, true);
    const onResize = () => c.resize();
    window.addEventListener('resize', onResize);
    return () => { window.removeEventListener('resize', onResize); c.dispose(); };
  }, [data]);

  if (loading) return <div style={s.loading}>加载中...</div>;

  // 计算总数
  const total = (data?.segments || []).reduce((sum, seg) => sum + seg.count, 0);

  return (
    <div>
      <h1 style={s.title}>👥 游客分层</h1>
      <p style={s.subtitle}>游客类型分布与偏好分析</p>

      {/* 分层卡片 */}
      <div style={s.cards}>
        <div style={{ ...s.card, borderTopColor: '#1976D2' }}>
          <div style={s.cardLabel}>游客总量</div>
          <div style={{ ...s.cardValue, color: '#1976d2' }}>{total}</div>
        </div>
        {(data?.segments || []).map((seg, i) => (
          <div key={seg.label} style={{
            ...s.card,
            borderTopColor: ['#43a047', '#ff8f00', '#7e57c2'][i] || '#1976d2',
          }}>
            <div style={s.cardLabel}>{seg.label}</div>
            <div style={{ ...s.cardValue, color: ['#43a047', '#ff8f00', '#7e57c2'][i] || '#1976d2' }}>
              {seg.count}
            </div>
            <div style={s.cardSub}>{total > 0 ? Math.round(seg.count / total * 100) : 0}%</div>
          </div>
        )).slice(0, 3)}
      </div>

      <div style={s.grid}>
        {/* 标签分布 */}
        <div style={s.chartBox}>
          <h3 style={s.chartTitle}>游客标签分布</h3>
          <div ref={tagPieRef} style={{ height: 320 }} />
        </div>

        {/* 偏好分布 */}
        <div style={s.chartBox}>
          <h3 style={s.chartTitle}>游览偏好分布</h3>
          {data?.preference_distribution ? (
            <div ref={prefPieRef} style={{ height: 320 }} />
          ) : (
            <div style={s.empty}>暂无偏好数据</div>
          )}
        </div>
      </div>
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  title: { fontSize: 22, fontWeight: 600, marginBottom: 4, color: '#1a1a2e' },
  subtitle: { fontSize: 13, color: '#999', marginBottom: 20 },
  loading: { textAlign: 'center', padding: 80, color: '#999', fontSize: 15 },
  empty: { textAlign: 'center', padding: 60, color: '#ccc' },
  cards: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 20 },
  card: {
    background: '#fff', borderRadius: 10, padding: '20px 24px',
    borderTop: '3px solid #1976D2', boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
  },
  cardLabel: { fontSize: 13, color: '#999', marginBottom: 8 },
  cardValue: { fontSize: 28, fontWeight: 700 },
  cardSub: { fontSize: 12, color: '#bbb', marginTop: 4 },
  grid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 },
  chartBox: {
    background: '#fff', borderRadius: 10, padding: 20,
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
  },
  chartTitle: { fontSize: 15, fontWeight: 600, marginBottom: 16, color: '#333' },
};
