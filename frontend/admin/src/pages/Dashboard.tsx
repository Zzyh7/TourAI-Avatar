/**
 * 数据概览页 —— 统计大屏
 */
import { useState, useEffect } from 'react';
import {
  getStatsOverview,
  getHotQA,
  getSentimentTrend,
  getDailyStats,
  type StatsOverview,
  type HotQA,
  type SentimentTrend,
  type DailyStats,
} from '../services/api';

export default function Dashboard() {
  const [overview, setOverview] = useState<StatsOverview | null>(null);
  const [hotQA, setHotQA] = useState<HotQA[]>([]);
  const [sentiment, setSentiment] = useState<SentimentTrend[]>([]);
  const [daily, setDaily] = useState<DailyStats[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [ov, hot, sent, dly] = await Promise.all([
        getStatsOverview(),
        getHotQA(10),
        getSentimentTrend(7),
        getDailyStats(7),
      ]);
      setOverview(ov);
      setHotQA(hot);
      setSentiment(sent);
      setDaily(dly);
    } catch (e) {
      console.error('加载统计数据失败:', e);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div style={styles.loading}>加载中...</div>;
  }

  // 计算情感趋势的最大值用于柱状图缩放
  const sentimentMax = Math.max(
    ...sentiment.map(s => Math.max(s['正面'] || 0, s['中性'] || 0, s['负面'] || 0)),
    1,
  );
  const dailyMax = Math.max(...daily.map(d => d.count), 1);

  return (
    <div>
      <h1 style={styles.title}>数据概览</h1>

      {/* 概览卡片 */}
      <div style={styles.cards}>
        <div style={{ ...styles.card, borderTopColor: '#1976D2' }}>
          <div style={styles.cardLabel}>服务人次</div>
          <div style={styles.cardValue}>{overview?.total_sessions ?? 0}</div>
        </div>
        <div style={{ ...styles.card, borderTopColor: '#4CAF50' }}>
          <div style={styles.cardLabel}>对话总数</div>
          <div style={styles.cardValue}>{overview?.total_conversations ?? 0}</div>
        </div>
        <div style={{ ...styles.card, borderTopColor: '#FF9800' }}>
          <div style={styles.cardLabel}>满意度</div>
          <div style={styles.cardValue}>{(overview?.sentiment_rate ?? 0)}%</div>
        </div>
        <div style={{ ...styles.card, borderTopColor: '#9C27B0' }}>
          <div style={styles.cardLabel}>平均延迟</div>
          <div style={styles.cardValue}>{overview?.avg_latency_ms ?? 0}ms</div>
        </div>
      </div>

      <div style={styles.grid}>
        {/* 每日服务量 */}
        <div style={styles.chartBox}>
          <h3 style={styles.chartTitle}>每日服务量（近7天）</h3>
          {daily.length === 0 ? (
            <div style={styles.emptyChart}>暂无数据</div>
          ) : (
            <div style={styles.barChart}>
              {daily.map(d => (
                <div key={d.date} style={styles.barCol}>
                  <div style={styles.barValue}>{d.count}</div>
                  <div style={{
                    ...styles.bar,
                    height: `${(d.count / dailyMax) * 160}px`,
                  }} />
                  <div style={styles.barLabel}>{d.date.slice(5)}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 情感趋势 */}
        <div style={styles.chartBox}>
          <h3 style={styles.chartTitle}>情感趋势（近7天）</h3>
          {sentiment.length === 0 ? (
            <div style={styles.emptyChart}>暂无数据</div>
          ) : (
            <div style={styles.sentimentChart}>
              {sentiment.map(s => {
                const total = (s['正面'] || 0) + (s['中性'] || 0) + (s['负面'] || 0) || 1;
                return (
                  <div key={s.date} style={styles.sentimentRow}>
                    <div style={styles.sentimentDate}>{s.date.slice(5)}</div>
                    <div style={styles.sentimentBar}>
                      <div style={{
                        ...styles.sentimentSeg,
                        width: `${((s['正面'] || 0) / total) * 100}%`,
                        background: '#4CAF50',
                      }} title={`正面: ${s['正面']}`} />
                      <div style={{
                        ...styles.sentimentSeg,
                        width: `${((s['中性'] || 0) / total) * 100}%`,
                        background: '#FF9800',
                      }} title={`中性: ${s['中性']}`} />
                      <div style={{
                        ...styles.sentimentSeg,
                        width: `${((s['负面'] || 0) / total) * 100}%`,
                        background: '#f44336',
                      }} title={`负面: ${s['负面']}`} />
                    </div>
                    <div style={styles.sentimentTotal}>{total}</div>
                  </div>
                );
              })}
            <div style={styles.legend}>
              <span><span style={{ ...styles.legendDot, background: '#4CAF50' }} /> 正面</span>
              <span><span style={{ ...styles.legendDot, background: '#FF9800' }} /> 中性</span>
              <span><span style={{ ...styles.legendDot, background: '#f44336' }} /> 负面</span>
            </div>
            </div>
          )}
        </div>
      </div>

      {/* 热门问答 */}
      <div style={styles.chartBox}>
        <h3 style={styles.chartTitle}>热门问答 Top 10</h3>
        {hotQA.length === 0 ? (
          <div style={styles.emptyChart}>暂无数据</div>
        ) : (
          <div style={styles.qaList}>
            {hotQA.map((qa, i) => (
              <div key={i} style={styles.qaRow}>
                <span style={styles.qaRank}>#{i + 1}</span>
                <span style={styles.qaText} title={qa.question}>
                  {qa.question.length > 50 ? qa.question.slice(0, 50) + '...' : qa.question}
                </span>
                <span style={styles.qaCount}>{qa.count} 次</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  title: {
    fontSize: 22,
    fontWeight: 600,
    marginBottom: 20,
    color: '#1a1a2e',
  },
  loading: {
    textAlign: 'center',
    padding: 80,
    color: '#999',
    fontSize: 15,
  },
  cards: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: 16,
    marginBottom: 20,
  },
  card: {
    background: '#fff',
    borderRadius: 10,
    padding: '20px 24px',
    borderTop: '3px solid #1976D2',
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
  },
  cardLabel: {
    fontSize: 13,
    color: '#999',
    marginBottom: 8,
  },
  cardValue: {
    fontSize: 28,
    fontWeight: 700,
    color: '#1a1a2e',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 16,
    marginBottom: 20,
  },
  chartBox: {
    background: '#fff',
    borderRadius: 10,
    padding: 20,
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
    marginBottom: 16,
  },
  chartTitle: {
    fontSize: 15,
    fontWeight: 600,
    marginBottom: 16,
    color: '#333',
  },
  emptyChart: {
    textAlign: 'center',
    padding: 40,
    color: '#ccc',
  },
  // 柱状图
  barChart: {
    display: 'flex',
    alignItems: 'flex-end',
    gap: 12,
    height: 220,
    padding: '0 4px',
  },
  barCol: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    height: '100%',
    justifyContent: 'flex-end',
  },
  barValue: {
    fontSize: 11,
    color: '#666',
    marginBottom: 4,
  },
  bar: {
    width: '100%',
    maxWidth: 40,
    background: 'linear-gradient(180deg, #1976D2, #64B5F6)',
    borderRadius: '4px 4px 0 0',
    minHeight: 4,
    transition: 'height 0.3s',
  },
  barLabel: {
    fontSize: 11,
    color: '#999',
    marginTop: 6,
  },
  // 情感趋势
  sentimentChart: {
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
  },
  sentimentRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
  },
  sentimentDate: {
    fontSize: 12,
    color: '#666',
    width: 45,
    flexShrink: 0,
  },
  sentimentBar: {
    flex: 1,
    height: 22,
    borderRadius: 4,
    overflow: 'hidden',
    display: 'flex',
    background: '#f0f0f0',
  },
  sentimentSeg: {
    height: '100%',
    transition: 'width 0.3s',
  },
  sentimentTotal: {
    fontSize: 12,
    color: '#999',
    width: 30,
    textAlign: 'right' as const,
  },
  legend: {
    display: 'flex',
    gap: 16,
    marginTop: 10,
    fontSize: 12,
    color: '#666',
  },
  legendDot: {
    display: 'inline-block',
    width: 10,
    height: 10,
    borderRadius: '50%',
    marginRight: 4,
    verticalAlign: 'middle',
  },
  // 热门问答
  qaList: {
    display: 'flex',
    flexDirection: 'column',
  },
  qaRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '10px 0',
    borderBottom: '1px solid #f5f5f5',
  },
  qaRank: {
    fontSize: 12,
    color: '#999',
    width: 30,
    flexShrink: 0,
  },
  qaText: {
    flex: 1,
    fontSize: 14,
    color: '#333',
  },
  qaCount: {
    fontSize: 12,
    color: '#1976D2',
    fontWeight: 500,
    flexShrink: 0,
  },
};
