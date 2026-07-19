/**
 * 问答质量分析 —— 满意度 + 提问分类 + Top Q & 答不上问题
 */
import { useState, useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { fetchQAQuality, fetchQuestionAnalysis, type QAQualityRes, type QuestionAnalysisRes } from '../services/api';

export default function QAAnalysis() {
  const [qa, setQA] = useState<QAQualityRes | null>(null);
  const [analysis, setAnalysis] = useState<QuestionAnalysisRes | null>(null);
  const [loading, setLoading] = useState(true);
  const pieRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    Promise.all([fetchQAQuality(), fetchQuestionAnalysis()])
      .then(([qaData, anData]) => {
        setQA(qaData);
        setAnalysis(anData);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!pieRef.current || !analysis?.categories) return;
    const c = echarts.init(pieRef.current);
    c.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c}条 ({d}%)' },
      legend: { bottom: 0, textStyle: { fontSize: 11 } },
      series: [{
        type: 'pie', radius: ['45%', '72%'], center: ['50%', '43%'],
        data: analysis.categories.map(cat => ({ value: cat.count, name: cat.name })),
        label: { formatter: '{b}\n{d}%' },
      }],
    }, true);
    const onResize = () => c.resize();
    window.addEventListener('resize', onResize);
    return () => { window.removeEventListener('resize', onResize); c.dispose(); };
  }, [analysis]);

  if (loading) return <div style={s.loading}>加载中...</div>;

  return (
    <div>
      <h1 style={s.title}>💬 问答分析</h1>
      <p style={s.subtitle}>AI 问答质量总览与提问分布</p>

      {/* 指标卡片 */}
      <div style={s.cards}>
        <div style={{ ...s.card, borderTopColor: '#C9A24E' }}>
          <div style={s.cardLabel}>满意度</div>
          <div style={{ ...s.cardValue, color: '#C9A24E' }}>{qa?.satisfaction_rate || 0}%</div>
        </div>
        <div style={{ ...s.card, borderTopColor: '#c0392b' }}>
          <div style={s.cardLabel}>答不上率</div>
          <div style={{ ...s.cardValue, color: '#c0392b' }}>{qa?.unable_rate || 0}%</div>
        </div>
        <div style={{ ...s.card, borderTopColor: '#B8860B' }}>
          <div style={s.cardLabel}>总回答数</div>
          <div style={{ ...s.cardValue, color: '#B8860B' }}>{qa?.total_answers || 0}</div>
        </div>
        <div style={{ ...s.card, borderTopColor: '#D4943A' }}>
          <div style={s.cardLabel}>无法回答</div>
          <div style={{ ...s.cardValue, color: '#D4943A' }}>{qa?.unable_to_answer || 0}</div>
          <div style={s.cardSub}>含"抱歉"的回复</div>
        </div>
      </div>

      <div style={s.grid}>
        {/* 提问分类饼图 */}
        <div style={s.chartBox}>
          <h3 style={s.chartTitle}>提问分类分布</h3>
          <div ref={pieRef} style={{ height: 350 }} />
        </div>

        <div>
          {/* Top 10 高频问题 */}
          <div style={s.chartBox}>
            <h3 style={s.chartTitle}>🔝 Top 10 高频问题</h3>
            {(analysis?.top_questions || []).length === 0 ? (
              <div style={s.empty}>暂无数据</div>
            ) : (
              <div>
                {(analysis?.top_questions || []).map((q, i) => (
                  <div key={i} style={s.qaRow}>
                    <span style={s.rank}>#{i + 1}</span>
                    <span style={s.qaText} title={q.question}>
                      {q.question.length > 40 ? q.question.slice(0, 40) + '...' : q.question}
                    </span>
                    <span style={s.count}>{q.count} 次</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 无法回答的问题 */}
      <div style={{ ...s.chartBox, marginTop: 16 }}>
        <h3 style={s.chartTitle}>⚠️ 无法回答的问题（知识缺口）</h3>
        {(analysis?.unable_questions || []).length === 0 ? (
          <div style={{ color: '#4caf50', fontSize: 14, padding: '20px 0', textAlign: 'center' }}>
            🎉 暂无无法回答的问题！
          </div>
        ) : (
          <div>
            {(analysis?.unable_questions || []).slice(0, 15).map((q, i) => (
              <div key={i} style={s.qaRow}>
                <span style={s.rank}>#{i + 1}</span>
                <span style={s.qaText} title={q.question}>{q.question}</span>
                <span style={s.count}>{q.count} 次</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  title: { fontSize: 22, fontWeight: 600, marginBottom: 4, color: '#4A3028' },
  subtitle: { fontSize: 13, color: '#8B7355', marginBottom: 20 },
  loading: { textAlign: 'center', padding: 80, color: '#8B7355', fontSize: 15 },
  empty: { textAlign: 'center', padding: 40, color: '#ccc' },
  cards: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 20 },
  card: {
    background: '#fff', borderRadius: 10, padding: '20px 24px',
    borderTop: '3px solid #C9A24E', boxShadow: '0 1px 4px rgba(74,48,40,0.06)',
  },
  cardLabel: { fontSize: 13, color: '#8B7355', marginBottom: 8 },
  cardValue: { fontSize: 28, fontWeight: 700 },
  cardSub: { fontSize: 12, color: '#8B7355', marginTop: 4 },
  grid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 },
  chartBox: {
    background: '#fff', borderRadius: 10, padding: 20,
    boxShadow: '0 1px 4px rgba(74,48,40,0.06)',
  },
  chartTitle: { fontSize: 15, fontWeight: 600, marginBottom: 16, color: '#4A3028' },
  qaRow: {
    display: 'flex', alignItems: 'center', gap: 12,
    padding: '10px 0', borderBottom: '1px solid #FFF9ED',
  },
  rank: { fontSize: 12, color: '#8B7355', width: 30, flexShrink: 0 },
  qaText: { flex: 1, fontSize: 14, color: '#4A3028' },
  count: { fontSize: 12, color: '#B8860B', fontWeight: 500, flexShrink: 0 },
};
