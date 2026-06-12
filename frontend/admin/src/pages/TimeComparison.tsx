/**
 * 时间对比分析 —— 今日 vs 昨日 vs 本周趋势
 */
import { useState, useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { fetchTimeComparison, type TimeComparisonRes } from '../services/api';

export default function TimeComparison() {
  const [data, setData] = useState<TimeComparisonRes | null>(null);
  const [loading, setLoading] = useState(true);
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchTimeComparison()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!chartRef.current || !data?.week_daily) return;
    const c = echarts.init(chartRef.current);
    c.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['对话数', '满意度%'], bottom: 0 },
      grid: { left: '3%', right: '6%', bottom: '12%', top: '5%', containLabel: true },
      xAxis: {
        type: 'category',
        data: data.week_daily.map((_, i) => ['一', '二', '三', '四', '五', '六', '日'][i]),
      },
      yAxis: [
        { type: 'value', name: '条' },
        { type: 'value', name: '%', min: 0, max: 100 },
      ],
      series: [
        {
          name: '对话数', type: 'bar',
          data: data.week_daily.map(d => d.conversations),
          itemStyle: { color: '#90caf9', borderRadius: 4 }, barWidth: '40%',
        },
        {
          name: '满意度%', type: 'line', yAxisIndex: 1,
          data: data.week_daily.map(d => d.rate),
          smooth: true, itemStyle: { color: '#66bb6a' }, lineStyle: { width: 3 },
        },
      ],
    }, true);
    const onResize = () => c.resize();
    window.addEventListener('resize', onResize);
    return () => { window.removeEventListener('resize', onResize); c.dispose(); };
  }, [data]);

  if (loading) return <div style={s.loading}>加载中...</div>;

  const today = data?.today;
  const yesterday = data?.yesterday;

  return (
    <div>
      <h1 style={s.title}>📅 时间对比</h1>
      <p style={s.subtitle}>对话量与满意度的日/周对比分析</p>

      {/* 对比卡片 */}
      <div style={s.cards}>
        <div style={{ ...s.card, borderTopColor: '#1976D2' }}>
          <div style={s.cardLabel}>今日对话数</div>
          <div style={{ ...s.cardValue, color: '#1976d2' }}>{today?.conversations || 0}</div>
          <div style={s.cardSub}>满意度 {today?.rate || 0}%</div>
        </div>
        <div style={{ ...s.card, borderTopColor: '#FF9800' }}>
          <div style={s.cardLabel}>昨日对话数</div>
          <div style={{ ...s.cardValue, color: '#FF9800' }}>{yesterday?.conversations || 0}</div>
          <div style={s.cardSub}>满意度 {yesterday?.rate || 0}%</div>
        </div>
        <div style={{ ...s.card, borderTopColor: '#43a047' }}>
          <div style={s.cardLabel}>本周总计</div>
          <div style={{ ...s.cardValue, color: '#43a047' }}>{data?.this_week_total || 0}</div>
          <div style={s.cardSub}>上周 {data?.last_week_total || 0}</div>
        </div>
        <div style={{
          ...s.card, borderTopColor: (data?.week_change || 0) >= 0 ? '#43a047' : '#ef5350',
        }}>
          <div style={s.cardLabel}>周环比变化</div>
          <div style={{
            ...s.cardValue,
            color: (data?.week_change || 0) >= 0 ? '#43a047' : '#ef5350',
          }}>
            {(data?.week_change || 0) >= 0 ? '↑' : '↓'}{Math.abs(data?.week_change || 0)}%
          </div>
          <div style={s.cardSub}>vs 上周</div>
        </div>
      </div>

      {/* 周趋势图 */}
      <div style={s.chartBox}>
        <h3 style={s.chartTitle}>本周每日趋势</h3>
        <div ref={chartRef} style={{ height: 360 }} />
      </div>
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  title: { fontSize: 22, fontWeight: 600, marginBottom: 4, color: '#1a1a2e' },
  subtitle: { fontSize: 13, color: '#999', marginBottom: 20 },
  loading: { textAlign: 'center', padding: 80, color: '#999', fontSize: 15 },
  cards: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 20 },
  card: {
    background: '#fff', borderRadius: 10, padding: '20px 24px',
    borderTop: '3px solid #1976D2', boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
  },
  cardLabel: { fontSize: 13, color: '#999', marginBottom: 8 },
  cardValue: { fontSize: 28, fontWeight: 700 },
  cardSub: { fontSize: 12, color: '#bbb', marginTop: 4 },
  chartBox: {
    background: '#fff', borderRadius: 10, padding: 20,
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
  },
  chartTitle: { fontSize: 15, fontWeight: 600, marginBottom: 16, color: '#333' },
};
