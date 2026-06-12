/**
 * 负面反馈分析 —— 分类柱状图 + 样本列表 + AI 优化建议
 */
import { useState, useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { fetchNegativeAnalysis, type NegativeAnalysisRes } from '../services/api';

export default function NegativeFeedback() {
  const [data, setData] = useState<NegativeAnalysisRes | null>(null);
  const [loading, setLoading] = useState(true);
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchNegativeAnalysis()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!chartRef.current || !data?.categories) return;
    const c = echarts.init(chartRef.current);
    const cats = [...(data.categories || [])].reverse();
    c.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: '15%', right: '10%', top: '3%', bottom: '5%', containLabel: true },
      xAxis: { type: 'value', name: '次数' },
      yAxis: { type: 'category', data: cats.map(c => c.name), axisLabel: { fontSize: 12 } },
      series: [{
        type: 'bar', data: cats.map(c => c.count),
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#ef5350' }, { offset: 1, color: '#ffcdd2' },
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
      <h1 style={s.title}>⚠️ 负面反馈</h1>
      <p style={s.subtitle}>用户负面情绪分析与 AI 优化建议</p>

      <div style={s.grid}>
        {/* 负面分类柱状图 */}
        <div style={s.chartBox}>
          <h3 style={s.chartTitle}>负面反馈分类</h3>
          <div ref={chartRef} style={{ height: 380 }} />
        </div>

        {/* 负面样本 + AI建议 */}
        <div>
          <div style={s.chartBox}>
            <h3 style={s.chartTitle}>📋 负面反馈样本</h3>
            {(data?.samples || []).length === 0 ? (
              <div style={s.empty}>暂无负面反馈</div>
            ) : (
              <div style={{ maxHeight: 280, overflow: 'auto' }}>
                {(data?.samples || []).slice(0, 10).map((item, i) => (
                  <div key={i} style={s.sampleRow}>
                    <div style={s.sampleQ} title={item.question}>
                      {item.question.length > 50 ? item.question.slice(0, 50) + '...' : item.question}
                    </div>
                    <span style={{
                      ...s.sampleTag,
                      background: item.sentiment === '负面' ? '#ffebee' : '#fff3e0',
                      color: item.sentiment === '负面' ? '#c62828' : '#e65100',
                    }}>
                      {item.sentiment}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div style={{ ...s.chartBox, marginTop: 16, borderLeft: '4px solid #1976d2' }}>
            <h3 style={s.chartTitle}>🤖 AI 优化建议</h3>
            <div style={{ fontSize: 14, color: '#555', lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>
              {data?.suggestion || '暂无优化建议'}
            </div>
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
  sampleRow: {
    display: 'flex', alignItems: 'center', gap: 8,
    padding: '10px 0', borderBottom: '1px solid #f5f5f5',
  },
  sampleQ: { flex: 1, fontSize: 13, color: '#555' },
  sampleTag: {
    display: 'inline-block', padding: '2px 8px', borderRadius: 4,
    fontSize: 11, fontWeight: 500, flexShrink: 0,
  },
};
