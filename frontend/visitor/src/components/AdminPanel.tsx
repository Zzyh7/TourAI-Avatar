/**
 * 景区导览后台管理 —— 数据报表 / 知识库管理 / 对话记录
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import * as echarts from 'echarts';

const API = '/api';

// ==================== 数据报表 Tab ====================
function StatsTab() {
  const trendRef = useRef<HTMLDivElement>(null);
  const pieRef = useRef<HTMLDivElement>(null);
  const [overview, setOverview] = useState<any>({});
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [ov, trend] = await Promise.all([
        fetch(`${API}/admin/stats/overview`).then(r => r.json()),
        fetch(`${API}/admin/stats/sentiment?days=7`).then(r => r.json()),
      ]);
      setOverview(ov);
      renderCharts(trend);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  const renderCharts = (trend: any[]) => {
    if (!trendRef.current || !pieRef.current) return;

    const trendChart = echarts.init(trendRef.current);
    const pieChart = echarts.init(pieRef.current);

    if (trend.length > 0) {
      trendChart.setOption({
        tooltip: { trigger: 'axis' },
        legend: { data: ['正面', '中性', '负面'], bottom: 0 },
        grid: { left: '3%', right: '4%', bottom: '12%', top: '5%', containLabel: true },
        xAxis: { type: 'category', data: trend.map((d: any) => d.date) },
        yAxis: { type: 'value' },
        series: [
          { name: '正面', type: 'line', data: trend.map((d: any) => d['正面'] || 0), smooth: true, itemStyle: { color: '#66bb6a' }, areaStyle: { color: 'rgba(102,187,106,0.1)' } },
          { name: '中性', type: 'line', data: trend.map((d: any) => d['中性'] || 0), smooth: true, itemStyle: { color: '#42a5f5' }, lineStyle: { type: 'dashed' } },
          { name: '负面', type: 'line', data: trend.map((d: any) => d['负面'] || 0), smooth: true, itemStyle: { color: '#ef5350' }, lineStyle: { type: 'dotted' }, areaStyle: { color: 'rgba(239,83,80,0.1)' } },
        ],
      });

      let pos = 0, neu = 0, neg = 0;
      trend.forEach((d: any) => { pos += d['正面'] || 0; neu += d['中性'] || 0; neg += d['负面'] || 0; });
      const total = pos + neu + neg || 1;
      pieChart.setOption({
        tooltip: { trigger: 'item', formatter: '{b}: {c}条 ({d}%)' },
        legend: { bottom: 0 },
        graphic: [{ type: 'text', left: 'center', top: '42%', style: { text: `满意度\n${((pos / total) * 100).toFixed(1)}%`, textAlign: 'center', fill: '#66bb6a', fontSize: 16, fontWeight: 'bold' } }],
        series: [{
          type: 'pie', radius: ['50%', '70%'], center: ['50%', '43%'],
          label: { formatter: '{b}\n{d}%' },
          data: [
            { value: pos, name: '😊 正面', itemStyle: { color: '#66bb6a' } },
            { value: neu, name: '😐 中性', itemStyle: { color: '#42a5f5' } },
            { value: neg, name: '😟 负面', itemStyle: { color: '#ef5350' } },
          ],
        }],
      });
    } else {
      [trendChart, pieChart].forEach(c => c.setOption({
        title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { color: '#999', fontSize: 14 } },
        xAxis: { show: false }, yAxis: { show: false }, series: [],
      }));
    }
  };

  useEffect(() => { fetchData(); }, [fetchData]);
  useEffect(() => {
    const onResize = () => { /* charts handle resize internally */ };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  return (
    <div>
      <div style={styles.statRow}>
        <StatCard label="💬 服务人次" value={overview.total_sessions || 0} sub="总会话数" />
        <StatCard label="📝 对话总数" value={overview.total_conversations || 0} sub="用户+AI消息" />
        <StatCard label="😊 满意度" value={(overview.sentiment_rate || 0) + '%'} sub="正面占比" color="#66bb6a" />
        <StatCard label="⚡ 平均延迟" value={Math.round(overview.avg_latency_ms || 0) + 'ms'} sub="响应时间" color="#ffa726" />
      </div>
      <div style={styles.chartRow}>
        <div style={styles.chartBox}>
          <h3 style={styles.chartTitle}>📈 情感趋势（近7天）</h3>
          <div ref={trendRef} style={{ width: '100%', height: 350 }} />
        </div>
        <div style={styles.chartBox}>
          <h3 style={styles.chartTitle}>🍩 满意度分布（近7天）</h3>
          <div ref={pieRef} style={{ width: '100%', height: 350 }} />
        </div>
      </div>
      <div style={{ textAlign: 'right', padding: '0 24px' }}>
        <button onClick={fetchData} style={styles.btn}>🔄 刷新</button>
      </div>
    </div>
  );
}

function StatCard({ label, value, sub, color = '#4fc3f7' }: { label: string; value: any; sub: string; color?: string }) {
  return (
    <div style={styles.statCard}>
      <div style={styles.statLabel}>{label}</div>
      <div style={{ ...styles.statValue, color }}>{value}</div>
      <div style={styles.statSub}>{sub}</div>
    </div>
  );
}

// ==================== 知识库管理 Tab ====================
function KnowledgeTab() {
  const [docs, setDocs] = useState<any[]>([]);
  const [faqCount, setFaqCount] = useState(0);
  const [uploadMsg, setUploadMsg] = useState('');
  const [faqMsg, setFaqMsg] = useState('');
  const [faqJson, setFaqJson] = useState('');

  const fetchDocs = async () => {
    try {
      const [d, f] = await Promise.all([
        fetch(`${API}/rag/admin/documents`).then(r => r.json()),
        fetch(`${API}/rag/health`).then(r => r.json()),
      ]);
      setDocs(d.documents || []);
      setFaqCount(f.stats?.faq_pairs || 0);
    } catch (e) { console.error(e); }
  };

  useEffect(() => { fetchDocs(); }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadMsg('上传中...');
    const form = new FormData();
    form.append('file', file);
    try {
      const resp = await fetch(`${API}/rag/admin/upload`, { method: 'POST', body: form });
      const data = await resp.json();
      setUploadMsg(data.message || '上传成功');
      fetchDocs();
    } catch (err: any) {
      setUploadMsg('上传失败: ' + err.message);
    }
  };

  const handleFaqImport = async () => {
    if (!faqJson.trim()) return;
    setFaqMsg('导入中...');
    try {
      const pairs = JSON.parse(faqJson);
      const resp = await fetch(`${API}/rag/admin/faq/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ faq_pairs: pairs }),
      });
      const data = await resp.json();
      setFaqMsg(data.message || '导入成功');
      setFaqJson('');
      fetchDocs();
    } catch (err: any) {
      setFaqMsg('导入失败: ' + (err.message || 'JSON格式错误'));
    }
  };

  const handleDelete = async (docId: number) => {
    if (!confirm('确定删除此文档？')) return;
    await fetch(`${API}/rag/admin/documents/${docId}`, { method: 'DELETE' });
    fetchDocs();
  };

  return (
    <div style={{ padding: 24 }}>
      {/* 文档上传 */}
      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>📄 文档上传</h3>
        <p style={styles.hint}>支持 PDF / Word / TXT / Markdown，上传后自动分块向量化</p>
        <input type="file" accept=".pdf,.docx,.txt,.md" onChange={handleUpload} style={styles.fileInput} />
        {uploadMsg && <p style={styles.msg}>{uploadMsg}</p>}
      </div>

      {/* FAQ 导入 */}
      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>❓ FAQ 问答对导入</h3>
        <p style={styles.hint}>当前已导入 {faqCount} 条 FAQ</p>
        <textarea
          value={faqJson}
          onChange={e => setFaqJson(e.target.value)}
          placeholder={`[{"question": "景区几点开门？", "answer": "早上8点开门。"}]`}
          style={styles.textarea}
          rows={5}
        />
        <br />
        <button onClick={handleFaqImport} style={styles.btn}>导入 FAQ</button>
        {faqMsg && <p style={styles.msg}>{faqMsg}</p>}
      </div>

      {/* 文档列表 */}
      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>📋 已上传文档 ({docs.length})</h3>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>ID</th>
              <th style={styles.th}>文件名</th>
              <th style={styles.th}>类型</th>
              <th style={styles.th}>块数</th>
              <th style={styles.th}>大小</th>
              <th style={styles.th}>上传时间</th>
              <th style={styles.th}>操作</th>
            </tr>
          </thead>
          <tbody>
            {docs.map((d: any) => (
              <tr key={d.id}>
                <td style={styles.td}>{d.id}</td>
                <td style={styles.td}>{d.filename}</td>
                <td style={styles.td}>{d.file_type}</td>
                <td style={styles.td}>{d.chunk_count}</td>
                <td style={styles.td}>{Math.round(d.size_bytes / 1024)} KB</td>
                <td style={styles.td}>{d.uploaded_at}</td>
                <td style={styles.td}>
                  <button onClick={() => handleDelete(d.id)} style={styles.delBtn}>删除</button>
                </td>
              </tr>
            ))}
            {docs.length === 0 && (
              <tr><td colSpan={7} style={{ ...styles.td, textAlign: 'center', color: '#999' }}>暂无文档</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ==================== 对话记录 Tab ====================
function ConversationsTab() {
  const [sessions, setSessions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const ov = await fetch(`${API}/admin/stats/overview`).then(r => r.json());
      // Get hot questions as a proxy for recent activity
      const hot = await fetch(`${API}/admin/stats/qa-hot?limit=20`).then(r => r.json());
      setSessions(hot || []);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  useEffect(() => { fetchData(); }, []);

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3 style={styles.sectionTitle}>💬 热门提问 Top 20</h3>
        <button onClick={fetchData} style={styles.btn}>🔄 刷新</button>
      </div>
      <table style={styles.table}>
        <thead>
          <tr>
            <th style={styles.th}>#</th>
            <th style={styles.th}>问题</th>
            <th style={styles.th}>提问次数</th>
          </tr>
        </thead>
        <tbody>
          {sessions.map((s: any, i: number) => (
            <tr key={i}>
              <td style={styles.td}>{i + 1}</td>
              <td style={{ ...styles.td, maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.question}</td>
              <td style={styles.td}>{s.count}</td>
            </tr>
          ))}
          {sessions.length === 0 && (
            <tr><td colSpan={3} style={{ ...styles.td, textAlign: 'center', color: '#999' }}>暂无对话记录</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

// ==================== 主 AdminPanel ====================
export default function AdminPanel() {
  const [tab, setTab] = useState<'stats' | 'knowledge' | 'conversations'>('stats');

  const tabs = [
    { key: 'stats' as const, label: '📊 数据报表' },
    { key: 'knowledge' as const, label: '📚 知识库管理' },
    { key: 'conversations' as const, label: '💬 对话记录' },
  ];

  return (
    <div style={styles.panel}>
      <div style={styles.tabBar}>
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              ...styles.tab,
              ...(tab === t.key ? styles.tabActive : {}),
            }}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div style={styles.tabContent}>
        {tab === 'stats' && <StatsTab />}
        {tab === 'knowledge' && <KnowledgeTab />}
        {tab === 'conversations' && <ConversationsTab />}
      </div>
    </div>
  );
}

// ==================== 样式 ====================
const styles: Record<string, React.CSSProperties> = {
  panel: {
    display: 'flex', flexDirection: 'column', height: '100%',
    background: '#f5f7fa', fontFamily: "'PingFang SC','Microsoft YaHei',sans-serif",
  },
  tabBar: {
    display: 'flex', gap: 0, background: '#fff', borderBottom: '2px solid #e8e8e8',
    padding: '0 24px',
  },
  tab: {
    padding: '14px 24px', border: 'none', background: 'transparent',
    fontSize: 15, cursor: 'pointer', color: '#666',
    borderBottom: '2px solid transparent', marginBottom: -2,
    transition: 'all 0.2s',
  },
  tabActive: {
    color: '#1976d2', borderBottomColor: '#1976d2', fontWeight: 600,
  },
  tabContent: { flex: 1, overflow: 'auto' },

  // Stats
  statRow: { display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 16, padding: 24 },
  statCard: { background: '#fff', borderRadius: 10, padding: 20, textAlign: 'center', boxShadow: '0 1px 4px rgba(0,0,0,0.06)' },
  statLabel: { fontSize: 13, color: '#999', marginBottom: 8 },
  statValue: { fontSize: 32, fontWeight: 700 },
  statSub: { fontSize: 12, color: '#bbb', marginTop: 4 },
  chartRow: { display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16, padding: '0 24px 16px' },
  chartBox: { background: '#fff', borderRadius: 10, padding: 20, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' },
  chartTitle: { fontSize: 15, fontWeight: 600, color: '#333', marginBottom: 12 },

  // Knowledge
  section: { background: '#fff', borderRadius: 10, padding: 20, marginBottom: 16, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' },
  sectionTitle: { fontSize: 16, fontWeight: 600, color: '#333', margin: '0 0 8px 0' },
  hint: { fontSize: 13, color: '#999', marginBottom: 12 },
  fileInput: { fontSize: 14 },
  textarea: { width: '100%', maxWidth: 600, padding: 10, borderRadius: 6, border: '1px solid #ddd', fontSize: 13, fontFamily: 'monospace' },
  msg: { fontSize: 13, color: '#1976d2', marginTop: 8 },

  // Table
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: { textAlign: 'left', padding: '10px 12px', borderBottom: '2px solid #e8e8e8', color: '#666', fontWeight: 600, background: '#fafafa' },
  td: { padding: '10px 12px', borderBottom: '1px solid #f0f0f0', color: '#333' },

  // Buttons
  btn: {
    padding: '8px 20px', background: '#1976d2', color: '#fff', border: 'none',
    borderRadius: 6, fontSize: 14, cursor: 'pointer', fontWeight: 500,
  },
  delBtn: {
    padding: '4px 12px', background: '#ef5350', color: '#fff', border: 'none',
    borderRadius: 4, fontSize: 12, cursor: 'pointer',
  },
};
