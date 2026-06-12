/**
 * 数据大屏 —— ECharts 综合仪表盘
 */
import { useState, useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { fetchFullDashboard, type FullDashboard } from '../services/api';

function useChart(ref: React.RefObject<HTMLDivElement | null>, option: any, deps: any[]) {
  useEffect(() => {
    if (!ref.current) return;
    const c = echarts.init(ref.current);
    c.setOption(option, true);
    const onResize = () => c.resize();
    window.addEventListener('resize', onResize);
    return () => { window.removeEventListener('resize', onResize); c.dispose(); };
  }, deps);
}

export default function Dashboard() {
  const [data, setData] = useState<FullDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const trendRef = useRef<HTMLDivElement>(null);
  const pieRef = useRef<HTMLDivElement>(null);
  const hourRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchFullDashboard()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  // 本周趋势
  useChart(trendRef, {
    tooltip: { trigger: 'axis' },
    legend: { data: ['对话数', '满意度%'], bottom: 0 },
    grid: { left: '3%', right: '6%', bottom: '12%', top: '5%', containLabel: true },
    xAxis: {
      type: 'category',
      data: (data?.time_comparison?.week_daily || []).map((_, i: number) =>
        ['一', '二', '三', '四', '五', '六', '日'][i]
      ),
    },
    yAxis: [
      { type: 'value', name: '条' },
      { type: 'value', name: '%', min: 0, max: 100 },
    ],
    series: [
      {
        name: '对话数', type: 'bar',
        data: (data?.time_comparison?.week_daily || []).map((d: any) => d.conversations),
        itemStyle: { color: '#90caf9', borderRadius: 4 }, barWidth: '40%',
      },
      {
        name: '满意度%', type: 'line', yAxisIndex: 1,
        data: (data?.time_comparison?.week_daily || []).map((d: any) => d.rate),
        smooth: true, itemStyle: { color: '#66bb6a' }, lineStyle: { width: 3 },
      },
    ],
  }, [data]);

  // 情感分布
  useChart(pieRef, {
    tooltip: { trigger: 'item', formatter: '{b}: {c}条 ({d}%)' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie', radius: ['50%', '70%'], center: ['50%', '43%'],
      data: [
        { value: data?.qa_quality?.sentiment?.positive || 0, name: '正面', itemStyle: { color: '#66bb6a' } },
        { value: data?.qa_quality?.sentiment?.neutral || 0, name: '中性', itemStyle: { color: '#42a5f5' } },
        { value: data?.qa_quality?.sentiment?.negative || 0, name: '负面', itemStyle: { color: '#ef5350' } },
      ],
    }],
  }, [data]);

  // 24小时交互分布
  useChart(hourRef, {
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', top: '5%', bottom: '5%', containLabel: true },
    xAxis: {
      type: 'category',
      data: (data?.interaction?.hourly_distribution || []).map((h: any) => h.hour + '时'),
      axisLabel: { fontSize: 10 },
    },
    yAxis: { type: 'value' },
    series: [{
      type: 'bar',
      data: (data?.interaction?.hourly_distribution || []).map((h: any) => h.count),
      itemStyle: { color: '#1976d2', borderRadius: 2 },
    }],
  }, [data]);

  if (loading) {
    return <div style={s.loading}>加载中...</div>;
  }

  const inter = data?.interaction;
  const qa = data?.qa_quality;
  const comp = data?.time_comparison;

  return (
    <div>
      <h1 style={s.title}>📊 数据大屏</h1>
      <p style={s.subtitle}>景区导览综合运营数据一览</p>

      {/* 核心指标卡片 */}
      <div style={s.cards}>
        <div style={{ ...s.card, borderTopColor: '#1976D2' }}>
          <div style={s.cardLabel}>今日服务人次</div>
          <div style={{ ...s.cardValue, color: '#1976d2' }}>{inter?.today?.sessions || 0}</div>
          <div style={s.cardSub}>昨日 {inter?.yesterday?.sessions || 0}</div>
        </div>
        <div style={{ ...s.card, borderTopColor: '#43a047' }}>
          <div style={s.cardLabel}>今日对话数</div>
          <div style={{ ...s.cardValue, color: '#43a047' }}>{inter?.today?.conversations || 0}</div>
          <div style={s.cardSub}>昨日 {inter?.yesterday?.conversations || 0}</div>
        </div>
        <div style={{ ...s.card, borderTopColor: '#ff8f00' }}>
          <div style={s.cardLabel}>本周服务人次</div>
          <div style={{ ...s.cardValue, color: '#ff8f00' }}>{inter?.week?.sessions || 0}</div>
          <div style={s.cardSub}>月度 {inter?.month?.sessions || 0}</div>
        </div>
        <div style={{ ...s.card, borderTopColor: '#7e57c2' }}>
          <div style={s.cardLabel}>回访游客(周)</div>
          <div style={{ ...s.cardValue, color: '#7e57c2' }}>{inter?.repeat_visitors_week || 0}</div>
          <div style={s.cardSub}>满意度 {qa?.satisfaction_rate || 0}%</div>
        </div>
      </div>

      {/* 图表第一行 */}
      <div style={s.grid}>
        <div style={s.chartBox}>
          <h3 style={s.chartTitle}>本周趋势（对话量 + 满意度）</h3>
          <div ref={trendRef} style={{ height: 300 }} />
        </div>
        <div style={s.chartBox}>
          <h3 style={s.chartTitle}>情感分布总览</h3>
          <div ref={pieRef} style={{ height: 300 }} />
        </div>
      </div>

      {/* 图表第二行 */}
      <div style={s.grid}>
        <div style={s.chartBox}>
          <h3 style={s.chartTitle}>全天交互时段分布（本月）</h3>
          <div ref={hourRef} style={{ height: 280 }} />
        </div>
        <div style={s.chartBox}>
          <h3 style={s.chartTitle}>AI 服务质量</h3>
          <div style={{ display: 'flex', justifyContent: 'space-around', textAlign: 'center', padding: 30 }}>
            <div>
              <div style={{ fontSize: 32, fontWeight: 700, color: '#43a047' }}>{qa?.satisfaction_rate || 0}%</div>
              <div style={{ fontSize: 13, color: '#999', marginTop: 4 }}>满意度</div>
            </div>
            <div>
              <div style={{ fontSize: 32, fontWeight: 700, color: '#ef5350' }}>{qa?.unable_rate || 0}%</div>
              <div style={{ fontSize: 13, color: '#999', marginTop: 4 }}>答不上率</div>
            </div>
            <div>
              <div style={{ fontSize: 32, fontWeight: 700, color: '#1976d2' }}>{qa?.total_answers || 0}</div>
              <div style={{ fontSize: 13, color: '#999', marginTop: 4 }}>总回答数</div>
            </div>
            <div>
              <div style={{
                fontSize: 32, fontWeight: 700,
                color: (comp?.week_change || 0) >= 0 ? '#43a047' : '#ef5350'
              }}>
                {(comp?.week_change || 0) >= 0 ? '↑' : '↓'}{Math.abs(comp?.week_change || 0)}%
              </div>
              <div style={{ fontSize: 13, color: '#999', marginTop: 4 }}>周同比变化</div>
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
  cards: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 20 },
  card: {
    background: '#fff', borderRadius: 10, padding: '20px 24px',
    borderTop: '3px solid #1976D2', boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
  },
  cardLabel: { fontSize: 13, color: '#999', marginBottom: 8 },
  cardValue: { fontSize: 28, fontWeight: 700 },
  cardSub: { fontSize: 12, color: '#bbb', marginTop: 4 },
  grid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 },
  chartBox: {
    background: '#fff', borderRadius: 10, padding: 20,
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
  },
  chartTitle: { fontSize: 15, fontWeight: 600, marginBottom: 16, color: '#333' },
};
