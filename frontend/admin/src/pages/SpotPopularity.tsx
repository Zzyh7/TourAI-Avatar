/**
 * 景点热度排行 —— ECharts 柱状图 + Top5 + 冷门标注
 */
import { useState, useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { fetchSpotPopularity, type SpotPopularityRes } from '../services/api';

export default function SpotPopularity() {
  const [data, setData] = useState<SpotPopularityRes | null>(null);
  const [loading, setLoading] = useState(true);
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchSpotPopularity()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!chartRef.current || !data) return;
    const c = echarts.init(chartRef.current);
    const ranking = [...(data.ranking || [])].reverse(); // 横向柱状图从下到上
    c.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: '12%', right: '10%', top: '3%', bottom: '5%', containLabel: true },
      xAxis: { type: 'value', name: '提及次数' },
      yAxis: { type: 'category', data: ranking.map(r => r.name), axisLabel: { fontSize: 12 } },
      series: [{
        type: 'bar', data: ranking.map(r => r.count),
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#1976d2' }, { offset: 1, color: '#64b5f6' },
          ]),
          borderRadius: [0, 4, 4, 0],
        },
        label: { show: true, position: 'right', fontSize: 12 },
      }],
    }, true);
    const onResize = () => c.resize();
    window.addEventListener('resize', onResize);
    return () => { window.removeEventListener('resize', onResize); c.dispose(); };
  }, [data]);

  if (loading) return <div style={s.loading}>加载中...</div>;

  return (
    <div>
      <h1 style={s.title}>🔥 景点热度</h1>
      <p style={s.subtitle}>基于用户提问关键词匹配（近30天），共 {data?.total_queries || 0} 条查询</p>

      <div style={s.grid}>
        <div style={s.chartBox}>
          <h3 style={s.chartTitle}>景点查询排行</h3>
          <div ref={chartRef} style={{ height: 420 }} />
        </div>

        <div>
          {/* Top 5 */}
          <div style={s.chartBox}>
            <h3 style={s.chartTitle}>🏆 热门 Top 5</h3>
            {(data?.top5 || []).length === 0 ? (
              <div style={s.empty}>暂无数据</div>
            ) : (
              <div>
                {data!.top5.map((spot, i) => (
                  <div key={spot.name} style={s.topRow}>
                    <span style={{ ...s.rank, color: i < 3 ? ['#FFD700', '#C0C0C0', '#CD7F32'][i] : '#999' }}>
                      #{i + 1}
                    </span>
                    <span style={s.spotName}>{spot.name}</span>
                    <span style={s.count}>{spot.count} 次</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 冷门景点 */}
          <div style={{ ...s.chartBox, marginTop: 16 }}>
            <h3 style={s.chartTitle}>❄️ 冷门景点（零查询）</h3>
            {(data?.cold_spots || []).length === 0 ? (
              <div style={{ color: '#4caf50', fontSize: 14, padding: '20px 0', textAlign: 'center' }}>
                🎉 所有景点均有被提及！
              </div>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {data!.cold_spots.map((spot: any) => (
                  <span key={spot.name} style={s.coldTag}>{spot.name}</span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  title: { fontSize: 22, fontWeight: 600, marginBottom: 4, color: '#1a1a2e' },
  subtitle: { fontSize: 13, color: '#999', marginBottom: 20 },
  loading: { textAlign: 'center', padding: 80, color: '#999', fontSize: 15 },
  empty: { textAlign: 'center', padding: 40, color: '#ccc' },
  grid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 },
  chartBox: {
    background: '#fff', borderRadius: 10, padding: 20,
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
  },
  chartTitle: { fontSize: 15, fontWeight: 600, marginBottom: 16, color: '#333' },
  topRow: {
    display: 'flex', alignItems: 'center', gap: 12,
    padding: '12px 0', borderBottom: '1px solid #f5f5f5',
  },
  rank: { fontSize: 16, fontWeight: 700, width: 36, flexShrink: 0 },
  spotName: { flex: 1, fontSize: 14, color: '#333' },
  count: { fontSize: 13, color: '#1976d2', fontWeight: 500 },
  coldTag: {
    display: 'inline-block', padding: '4px 12px', borderRadius: 4,
    background: '#f5f5f5', color: '#999', fontSize: 12,
  },
};
