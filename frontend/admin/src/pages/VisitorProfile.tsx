/**
 * 游客画像 —— 标签/偏好/客源地/分层综合分析
 */
import { useState, useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { fetchVisitorProfile, type VisitorProfileRes } from '../services/api';

export default function VisitorProfile() {
  const [data, setData] = useState<VisitorProfileRes | null>(null);
  const [loading, setLoading] = useState(true);

  // ECharts refs
  const tagPieRef = useRef<HTMLDivElement>(null);
  const prefPieRef = useRef<HTMLDivElement>(null);
  const originChartRef = useRef<HTMLDivElement>(null);
  const segChartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchVisitorProfile()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  // Section 1: 属性标签饼图
  useEffect(() => {
    if (!tagPieRef.current || !data?.attribute_tags?.length) return;
    const c = echarts.init(tagPieRef.current);
    c.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c}人 ({d}%)' },
      legend: { orient: 'vertical', right: 10, top: 'center', textStyle: { fontSize: 11 } },
      series: [{
        type: 'pie',
        radius: ['48%', '72%'],
        center: ['38%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
        data: data.attribute_tags.map(t => ({ name: t.name, value: t.value })),
        color: ['#ef5350', '#42a5f5', '#66bb6a', '#ffa726', '#ab47bc', '#26c6da'],
      }],
    }, true);
    const onResize = () => c.resize();
    window.addEventListener('resize', onResize);
    return () => { window.removeEventListener('resize', onResize); c.dispose(); };
  }, [data]);

  // Section 2: 偏好分布饼图
  useEffect(() => {
    if (!prefPieRef.current || !data?.preference_stats?.length) return;
    const c = echarts.init(prefPieRef.current);
    c.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c}人 ({d}%)' },
      legend: { orient: 'vertical', right: 10, top: 'center', textStyle: { fontSize: 11 } },
      series: [{
        type: 'pie',
        radius: ['48%', '72%'],
        center: ['38%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
        data: data.preference_stats.map(p => ({ name: p.name, value: p.value })),
        color: ['#43a047', '#ff8f00', '#1e88e5', '#8e24aa'],
      }],
    }, true);
    const onResize = () => c.resize();
    window.addEventListener('resize', onResize);
    return () => { window.removeEventListener('resize', onResize); c.dispose(); };
  }, [data]);

  // Section 3: 客源地分析
  useEffect(() => {
    if (!originChartRef.current || !data?.origin_analysis?.distribution?.length) return;
    const c = echarts.init(originChartRef.current);
    const dist = data.origin_analysis.distribution;
    c.setOption({
      tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].name}: ${p[0].value}人` },
      grid: { left: '3%', right: '8%', top: '5%', bottom: '5%', containLabel: true },
      xAxis: { type: 'value', show: false },
      yAxis: { type: 'category', data: dist.map(d => d.name), axisLabel: { fontSize: 13 } },
      series: [{
        type: 'bar',
        data: dist.map(d => d.value),
        barWidth: 28,
        itemStyle: {
          borderRadius: 4,
          color: (p: any) => ['#1e88e5', '#ffa726', '#66bb6a'][p.dataIndex] || '#90caf9',
        },
        label: { show: true, position: 'right', formatter: '{c}人' },
      }],
    }, true);
    const onResize = () => c.resize();
    window.addEventListener('resize', onResize);
    return () => { window.removeEventListener('resize', onResize); c.dispose(); };
  }, [data]);

  // Section 4: 分层柱状图
  useEffect(() => {
    if (!segChartRef.current || !data?.stratification?.segments?.length) return;
    const c = echarts.init(segChartRef.current);
    const segs = data.stratification.segments;
    const confidenceAlpha: Record<string, number> = { high: 1, medium: 0.55, low: 0.3 };
    c.setOption({
      tooltip: {
        trigger: 'axis',
        formatter: (p: any) => `${p[0].name}<br/>人数: ${p[0].value}<br/>置信度: ${segs[p[0].dataIndex].confidence}`,
      },
      grid: { left: '3%', right: '8%', top: '5%', bottom: '5%', containLabel: true },
      xAxis: { type: 'value', show: false },
      yAxis: { type: 'category', data: segs.map(s => s.label), axisLabel: { fontSize: 12, width: 80, overflow: 'truncate' } },
      series: [{
        type: 'bar',
        data: segs.map(s => ({ value: s.count, itemStyle: { color: `rgba(30,136,229,${confidenceAlpha[s.confidence] || 0.5})`, borderRadius: 4 } })),
        barWidth: 24,
        label: { show: true, position: 'right', formatter: '{c}人' },
      }],
    }, true);
    const onResize = () => c.resize();
    window.addEventListener('resize', onResize);
    return () => { window.removeEventListener('resize', onResize); c.dispose(); };
  }, [data]);

  if (loading) {
    return <div style={s.loading}>加载中...</div>;
  }

  const tags = data?.attribute_tags || [];
  const prefs = data?.preference_stats || [];
  const origin = data?.origin_analysis;
  const strat = data?.stratification;

  const topTag = tags[0]?.name || '-';
  const topPref = prefs[0]?.name || '-';
  const totalSeg = strat?.segments?.reduce((a, s) => a + s.count, 0) || 0;

  return (
    <div>
      <h1 style={s.title}>🧑 游客画像</h1>
      <p style={s.subtitle}>游客标签、偏好、客源地与分层综合分析</p>

      {/* 摘要卡片 */}
      <div style={s.cards}>
        <div style={{ ...s.card, borderTopColor: '#1976D2' }}>
          <div style={s.cardLabel}>游客总量（本月）</div>
          <div style={{ ...s.cardValue, color: '#1976d2' }}>{data?.total_visitors || 0}</div>
          <div style={s.cardSub}>活跃会话数</div>
        </div>
        <div style={{ ...s.card, borderTopColor: '#ef5350' }}>
          <div style={s.cardLabel}>最多属性标签</div>
          <div style={{ ...s.cardValue, color: '#ef5350', fontSize: 22 }}>{topTag}</div>
          <div style={s.cardSub}>共 {tags.length} 类标签</div>
        </div>
        <div style={{ ...s.card, borderTopColor: '#43a047' }}>
          <div style={s.cardLabel}>最多游玩偏好</div>
          <div style={{ ...s.cardValue, color: '#43a047', fontSize: 22 }}>{topPref}</div>
          <div style={s.cardSub}>共 {prefs.length} 类偏好</div>
        </div>
        <div style={{ ...s.card, borderTopColor: '#7e57c2' }}>
          <div style={s.cardLabel}>有效分层段</div>
          <div style={{ ...s.cardValue, color: '#7e57c2' }}>{totalSeg}</div>
          <div style={s.cardSub}>3 个分层维度</div>
        </div>
      </div>

      {/* ========== Section 1: 游客基础属性标签 ========== */}
      <div style={{ ...s.sectionHeader, marginTop: 24 }}>
        <h2 style={s.sectionTitle}>🏷️ 游客基础属性标签</h2>
        <p style={s.sectionDesc}>基于对话内容自动识别游客群体类型</p>
      </div>
      <div style={s.grid}>
        <div style={s.chartBox}>
          <h3 style={s.chartTitle}>群体占比分布</h3>
          {tags.length > 0 ? (
            <div ref={tagPieRef} style={{ height: 340 }} />
          ) : (
            <div style={s.emptyChart}>暂无标签数据</div>
          )}
        </div>
        <div style={s.chartBox}>
          <h3 style={s.chartTitle}>标签说明</h3>
          <table style={s.tagTable}>
            <thead>
              <tr><th style={s.th}>标签</th><th style={s.th}>人数</th><th style={s.th}>典型特征</th></tr>
            </thead>
            <tbody>
              {tags.map(t => (
                <tr key={t.name}>
                  <td style={s.td}><span style={s.tagBadge}>{t.name}</span></td>
                  <td style={s.td}>{t.value}人</td>
                  <td style={{ ...s.td, color: '#999', fontSize: 12 }}>
                    {tagDesc[t.name] || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ========== Section 2: 游玩偏好统计 ========== */}
      <div style={s.sectionHeader}>
        <h2 style={s.sectionTitle}>🎯 游玩偏好统计</h2>
        <p style={s.sectionDesc}>四类偏好人数分布 + 系统自动推荐游览路线</p>
      </div>
      <div style={s.grid}>
        <div style={s.chartBox}>
          <h3 style={s.chartTitle}>偏好分布</h3>
          {prefs.length > 0 ? (
            <div ref={prefPieRef} style={{ height: 340 }} />
          ) : (
            <div style={s.emptyChart}>暂无偏好数据</div>
          )}
        </div>
        <div style={s.chartBox}>
          <h3 style={s.chartTitle}>推荐路线概览</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 8 }}>
            {prefs.map(p => {
              const route = p.recommended_routes?.[0];
              return (
                <div key={p.name} style={s.routeCard}>
                  <div style={s.routeLabel}>📌 {route?.label || p.name}</div>
                  <div style={s.routeDesc}>{route?.description || ''}</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 8 }}>
                    {(route?.spots || []).length > 0
                      ? route!.spots.map(sp => <span key={sp} style={s.spotPill}>{sp}</span>)
                      : <span style={{ color: '#bbb', fontSize: 12 }}>暂无景点推荐</span>}
                  </div>
                  <div style={s.routeCount}>{p.value}人偏好</div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ========== Section 3: 客源地分析 ========== */}
      <div style={s.sectionHeader}>
        <h2 style={s.sectionTitle}>📍 客源地分析</h2>
        <p style={s.sectionDesc}>本地 / 周边城市 / 省外游客来源占比</p>
      </div>
      {origin && !origin.data_available && (
        <div style={s.warningBanner}>
          ⚠️ <strong>数据说明：</strong>{origin.note}
        </div>
      )}
      <div style={s.grid}>
        <div style={s.chartBox}>
          <h3 style={s.chartTitle}>客源地分布</h3>
          {origin?.distribution?.some(d => d.value > 0) ? (
            <div ref={originChartRef} style={{ height: 240 }} />
          ) : (
            <div style={s.emptyChart}>
              <div style={{ fontSize: 28, marginBottom: 8 }}>📭</div>
              <div>暂无足够客源地数据</div>
              <div style={{ fontSize: 12, color: '#bbb', marginTop: 4 }}>数据通过对话关键词推测</div>
            </div>
          )}
        </div>
        <div style={s.chartBox}>
          <h3 style={s.chartTitle}>营销建议</h3>
          <div style={{ padding: '12px 0' }}>
            <div style={s.adviceItem}>
              <span style={s.adviceIcon}>🏠</span>
              <div>
                <strong>本地游客</strong>
                <p style={s.adviceText}>推出年卡/季卡锁定周边常客，提升复访率</p>
              </div>
            </div>
            <div style={s.adviceItem}>
              <span style={s.adviceIcon}>🚗</span>
              <div>
                <strong>周边城市</strong>
                <p style={s.adviceText}>周末短途游营销，与沿线城市旅行社合作推广</p>
              </div>
            </div>
            <div style={s.adviceItem}>
              <span style={s.adviceIcon}>✈️</span>
              <div>
                <strong>省外游客</strong>
                <p style={s.adviceText}>线上平台种草+旅游攻略投放，拉长游客停留时间</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ========== Section 4: 游客分层数据 ========== */}
      <div style={s.sectionHeader}>
        <h2 style={s.sectionTitle}>📊 游客分层数据</h2>
        <p style={s.sectionDesc}>首次使用 / 多次复访 / 流失游客统计与可行性评估</p>
      </div>

      {/* 可行性分析卡片 */}
      {strat?.feasibility && (
        <div style={{
          ...s.feasibilityBox,
          borderLeftColor: strat.feasibility.score === 'high' ? '#43a047'
            : strat.feasibility.score === 'medium' ? '#ff8f00' : '#ef5350',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <strong style={{ fontSize: 15 }}>🔍 可行性分析</strong>
            <span style={{
              ...s.feasibilityBadge,
              background: strat.feasibility.score === 'high' ? '#e8f5e9'
                : strat.feasibility.score === 'medium' ? '#fff3e0' : '#ffebee',
              color: strat.feasibility.score === 'high' ? '#2e7d32'
                : strat.feasibility.score === 'medium' ? '#e65100' : '#c62828',
            }}>
              可行度: {
                strat.feasibility.score === 'high' ? '高' : strat.feasibility.score === 'medium' ? '中' : '低'
              }
            </span>
          </div>
          <p style={s.feasibilityText}>{strat.feasibility.analysis}</p>
          <p style={s.feasibilityRecommendation}>💡 {strat.feasibility.recommendation}</p>
        </div>
      )}

      {strat?.segments?.some(s => s.count > 0) ? (
        <div style={s.grid}>
          <div style={s.chartBox}>
            <h3 style={s.chartTitle}>分层分布（透明度=置信度）</h3>
            <div ref={segChartRef} style={{ height: 240 }} />
          </div>
          <div style={s.chartBox}>
            <h3 style={s.chartTitle}>分层详情</h3>
            <div style={{ padding: '8px 0' }}>
              {strat.segments.map(seg => (
                <div key={seg.label} style={s.segItem}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <strong style={{ fontSize: 13 }}>{seg.label}</strong>
                    <span style={{
                      fontSize: 11, padding: '2px 8px', borderRadius: 10, fontWeight: 600,
                      background: seg.confidence === 'high' ? '#e8f5e9' : seg.confidence === 'medium' ? '#fff3e0' : '#ffebee',
                      color: seg.confidence === 'high' ? '#2e7d32' : seg.confidence === 'medium' ? '#e65100' : '#c62828',
                    }}>
                      {seg.confidence === 'high' ? '高置信度' : seg.confidence === 'medium' ? '中置信度' : '低置信度'}
                    </span>
                  </div>
                  <div style={s.segBar}>
                    <div style={{
                      ...s.segFill,
                      width: `${totalSeg > 0 ? (seg.count / totalSeg * 100) : 0}%`,
                      opacity: seg.confidence === 'high' ? 1 : seg.confidence === 'medium' ? 0.6 : 0.35,
                    }} />
                  </div>
                  <div style={{ fontSize: 12, color: '#999', marginTop: 2 }}>{seg.count}人</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div style={s.emptyChart}>暂无分层数据。建议先积累更多游客会话数据。</div>
      )}
    </div>
  );
}

/* ========== 标签说明字典 ========== */
const tagDesc: Record<string, string> = {
  '亲子游客': '携带儿童的家庭',
  '研学学生': '学校/教育群体',
  '中老年观光': '高龄休闲观光',
  '青年徒步': '户外运动爱好者',
  '摄影爱好者': '拍照打卡为主',
  '外地短途游客': '周边短期出行',
};

/* ========== 内联样式 ========== */
const s: Record<string, React.CSSProperties> = {
  title: { fontSize: 22, fontWeight: 600, marginBottom: 4, color: '#1a1a2e' },
  subtitle: { fontSize: 13, color: '#999', marginBottom: 20 },
  loading: { textAlign: 'center', padding: 80, color: '#999', fontSize: 15 },
  cards: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 4 },
  card: {
    background: '#fff', borderRadius: 10, padding: '20px 24px',
    borderTop: '3px solid #1976D2', boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
  },
  cardLabel: { fontSize: 13, color: '#999', marginBottom: 8 },
  cardValue: { fontSize: 28, fontWeight: 700 },
  cardSub: { fontSize: 12, color: '#bbb', marginTop: 4 },

  // Sections
  sectionHeader: { marginTop: 28, marginBottom: 12 },
  sectionTitle: { fontSize: 17, fontWeight: 600, color: '#1a1a2e', margin: 0 },
  sectionDesc: { fontSize: 12, color: '#999', margin: '4px 0 0 0' },

  // Grid + chart
  grid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 8 },
  chartBox: {
    background: '#fff', borderRadius: 10, padding: 20,
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
  },
  chartTitle: { fontSize: 14, fontWeight: 600, marginBottom: 12, color: '#333' },
  emptyChart: { textAlign: 'center', padding: 60, color: '#bbb', fontSize: 14 },

  // Tag table
  tagTable: { width: '100%', borderCollapse: 'collapse', fontSize: 13 } as any,
  th: { textAlign: 'left', padding: '6px 10px', borderBottom: '2px solid #eee', color: '#999', fontSize: 12, fontWeight: 600 },
  td: { padding: '7px 10px', borderBottom: '1px solid #f5f5f5' },
  tagBadge: { display: 'inline-block', padding: '2px 10px', borderRadius: 12, fontSize: 12, background: '#e3f2fd', color: '#1565c0' },

  // Route cards
  routeCard: {
    flex: '1 1 45%', minWidth: 180, background: '#fafafa', borderRadius: 10, padding: 14,
    border: '1px solid #eee', position: 'relative',
  },
  routeLabel: { fontWeight: 600, fontSize: 13, color: '#333', marginBottom: 4 },
  routeDesc: { fontSize: 11, color: '#999', lineHeight: 1.5 },
  spotPill: { display: 'inline-block', padding: '2px 8px', background: '#e3f2fd', color: '#1565c0', borderRadius: 10, fontSize: 11 },
  routeCount: { marginTop: 8, fontSize: 11, color: '#bbb' },

  // Origin warning
  warningBanner: {
    background: '#fff8e1', borderLeft: '4px solid #ff8f00', borderRadius: 6,
    padding: '10px 16px', fontSize: 12, color: '#795548', marginBottom: 14, lineHeight: 1.6,
  },

  // Origin advice
  adviceItem: { display: 'flex', gap: 10, marginBottom: 14, alignItems: 'flex-start' },
  adviceIcon: { fontSize: 20, marginTop: 2 },
  adviceText: { margin: '4px 0 0', fontSize: 12, color: '#999' },

  // Stratification
  feasibilityBox: {
    background: '#e3f2fd', borderLeft: '4px solid #ff8f00', borderRadius: 8,
    padding: '16px 20px', marginBottom: 16,
  },
  feasibilityBadge: {
    fontSize: 11, fontWeight: 600, padding: '3px 10px', borderRadius: 10,
  },
  feasibilityText: { fontSize: 13, color: '#455a64', lineHeight: 1.7, marginBottom: 10 },
  feasibilityRecommendation: { fontSize: 12, color: '#78909c', fontStyle: 'italic', lineHeight: 1.6 },

  segItem: { marginBottom: 16 },
  segBar: { height: 10, background: '#f0f0f0', borderRadius: 5, overflow: 'hidden' },
  segFill: { height: '100%', background: '#1e88e5', borderRadius: 5, transition: 'width 0.6s ease' },
};
