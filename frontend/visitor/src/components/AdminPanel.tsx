/**
 * 景区导览后台管理 —— 数据大屏 / 感受度报告 / 知识库管理 / 对话记录
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import * as echarts from 'echarts';

const API = '/api';

// ==================== 数据大屏 Tab ====================
function DashboardTab() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const trendRef = useRef<HTMLDivElement>(null);
  const pieRef = useRef<HTMLDivElement>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${API}/admin/stats/dashboard`);
      const json = await resp.json();
      setData(json);
      setTimeout(() => renderCharts(json), 100);
    } catch (e) { console.error(e); }
    setLoading(false);
  }, []);

  const renderCharts = (d: any) => {
    if (!trendRef.current || !pieRef.current) return;
    const trendChart = echarts.init(trendRef.current);
    const pieChart = echarts.init(pieRef.current);

    // 本周趋势
    if (d.week?.daily?.length > 0) {
      const days = d.week.daily;
      trendChart.setOption({
        tooltip: { trigger: 'axis' },
        legend: { data: ['对话总数', '正面', '负面'], bottom: 0 },
        grid: { left: '3%', right: '4%', bottom: '12%', top: '5%', containLabel: true },
        xAxis: { type: 'category', data: days.map((dd: any) => dd.date.slice(5)) },
        yAxis: { type: 'value' },
        series: [
          { name: '对话总数', type: 'bar', data: days.map((dd: any) => dd.total), itemStyle: { color: '#1976d2', borderRadius: 4 }, barWidth: '40%' },
          { name: '正面', type: 'line', data: days.map((dd: any) => dd.positive), smooth: true, itemStyle: { color: '#66bb6a' }, lineStyle: { width: 3 } },
          { name: '负面', type: 'line', data: days.map((dd: any) => dd.negative), smooth: true, itemStyle: { color: '#ef5350' }, lineStyle: { width: 2, type: 'dashed' } },
        ],
      });
    }

    // 情感分布饼图
    const sd = d.sentiment_distribution || {};
    const pt = sd.positive || 0;
    const nt = sd.neutral || 0;
    const ng = sd.negative || 0;
    const total = pt + nt + ng || 1;
    pieChart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c}条 ({d}%)' },
      legend: { bottom: 0 },
      graphic: [{ type: 'text', left: 'center', top: '42%', style: { text: `满意度\n${((pt / total) * 100).toFixed(1)}%`, textAlign: 'center', fill: '#66bb6a', fontSize: 16, fontWeight: 'bold' } }],
      series: [{
        type: 'pie', radius: ['50%', '70%'], center: ['50%', '43%'],
        label: { formatter: '{b}\n{d}%' },
        data: [
          { value: pt, name: '正面', itemStyle: { color: '#66bb6a' } },
          { value: nt, name: '中性', itemStyle: { color: '#42a5f5' } },
          { value: ng, name: '负面', itemStyle: { color: '#ef5350' } },
        ],
      }],
    });
  };

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading && !data) return <div style={styles.loading}>加载中...</div>;

  const today = data?.today || {};
  const week = data?.week || {};
  const total = data?.total || {};

  return (
    <div style={{ padding: 24 }}>
      {/* 核心指标卡片 */}
      <div style={styles.cardRow}>
        <Card title="今日服务人次" value={today.sessions || 0} sub="会话数" color="#1976d2" />
        <Card title="今日对话数" value={today.conversations || 0} sub="满意度 " + (today.positive_rate || 0) + "%" color="#66bb6a" />
        <Card title="本周服务人次" value={week.sessions || 0} sub="对话 " + (week.conversations || 0) + " 条" color="#ffa726" />
        <Card title="累计服务人次" value={total.sessions || 0} sub="总对话 " + (total.conversations || 0) + " 条" color="#7e57c2" />
      </div>

      {/* 图表行 */}
      <div style={styles.chartRow}>
        <div style={styles.chartBox}>
          <h3 style={styles.chartTitle}>本周运营趋势（对话量 + 情感）</h3>
          <div ref={trendRef} style={{ width: '100%', height: 340 }} />
        </div>
        <div style={styles.chartBox}>
          <h3 style={styles.chartTitle}>整体情感分布</h3>
          <div ref={pieRef} style={{ width: '100%', height: 340 }} />
        </div>
      </div>

      {/* 热门提问 */}
      <div style={styles.section}>
        <h3 style={styles.chartTitle}>热门提问 Top 8</h3>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>#</th>
              <th style={styles.th}>问题</th>
              <th style={styles.th}>次数</th>
            </tr>
          </thead>
          <tbody>
            {(data?.hot_questions || []).map((q: any, i: number) => (
              <tr key={i}>
                <td style={styles.td}>{i + 1}</td>
                <td style={{ ...styles.td, maxWidth: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{q.question}</td>
                <td style={styles.td}>{q.count}</td>
              </tr>
            ))}
            {(!data?.hot_questions || data.hot_questions.length === 0) && (
              <tr><td colSpan={3} style={{ ...styles.td, textAlign: 'center', color: '#999' }}>暂无数据</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div style={{ textAlign: 'right', paddingTop: 8 }}>
        <button onClick={fetchData} style={styles.btn}>刷新数据</button>
      </div>
    </div>
  );
}

function Card({ title, value, sub, color }: { title: string; value: any; sub: string; color: string }) {
  return (
    <div style={{ ...styles.card, borderTop: `3px solid ${color}` }}>
      <div style={styles.cardTitle}>{title}</div>
      <div style={{ ...styles.cardValue, color }}>{value}</div>
      <div style={styles.cardSub}>{sub}</div>
    </div>
  );
}

// ==================== 感受度报告 Tab ====================
function ReportTab() {
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const concernRef = useRef<HTMLDivElement>(null);
  const trendRef = useRef<HTMLDivElement>(null);

  const fetchReport = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${API}/admin/stats/report?days=7`);
      const json = await resp.json();
      setReport(json);
      setTimeout(() => renderReportCharts(json), 100);
    } catch (e) { console.error(e); }
    setLoading(false);
  }, []);

  const renderReportCharts = (r: any) => {
    // 关注点柱状图
    if (concernRef.current && r.concerns) {
      const chart = echarts.init(concernRef.current);
      chart.setOption({
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        grid: { left: '3%', right: '10%', bottom: '5%', top: '5%', containLabel: true },
        xAxis: { type: 'value' },
        yAxis: { type: 'category', data: r.concerns.map((c: any) => c.name).reverse(), inverse: true, axisLabel: { fontSize: 12 } },
        series: [{
          type: 'bar', data: r.concerns.map((c: any) => c.count).reverse(),
          itemStyle: { color: '#1976d2', borderRadius: [0, 4, 4, 0] },
          label: { show: true, position: 'right', fontSize: 12 },
        }],
      });
    }

    // 每日情感趋势
    if (trendRef.current && r.daily_trend) {
      const chart = echarts.init(trendRef.current);
      chart.setOption({
        tooltip: { trigger: 'axis' },
        legend: { data: ['对话数', '正面', '负面'], bottom: 0 },
        grid: { left: '3%', right: '4%', bottom: '12%', top: '5%', containLabel: true },
        xAxis: { type: 'category', data: r.daily_trend.map((d: any) => d.date.slice(5)) },
        yAxis: { type: 'value' },
        series: [
          { name: '对话数', type: 'bar', data: r.daily_trend.map((d: any) => d.total), itemStyle: { color: '#90caf9', borderRadius: 4 }, barWidth: '35%' },
          { name: '正面', type: 'line', data: r.daily_trend.map((d: any) => d.positive), smooth: true, itemStyle: { color: '#66bb6a' }, lineStyle: { width: 3 } },
          { name: '负面', type: 'line', data: r.daily_trend.map((d: any) => d.negative), smooth: true, itemStyle: { color: '#ef5350' }, lineStyle: { width: 2, type: 'dashed' } },
        ],
      });
    }
  };

  useEffect(() => { fetchReport(); }, [fetchReport]);

  if (loading && !report) return <div style={styles.loading}>生成报告中...</div>;

  const s = report?.summary || {};

  return (
    <div style={{ padding: 24 }}>
      {/* 报告头部 */}
      <div style={styles.reportHeader}>
        <h2 style={{ margin: 0, fontSize: 20, color: '#333' }}>游客感受度报告</h2>
        <span style={{ color: '#999', fontSize: 13 }}>统计周期: {report?.period || '近7天'}</span>
      </div>

      {/* 核心指标 */}
      <div style={styles.cardRow}>
        <Card title="总对话数" value={s.total_conversations || 0} sub="" color="#1976d2" />
        <Card title="满意度" value={(s.satisfaction_rate || 0) + '%'} sub={`正面 ${s.positive || 0} 条`} color="#66bb6a" />
        <Card title="中性" value={s.neutral || 0} sub="条" color="#42a5f5" />
        <Card title="负面" value={s.negative || 0} sub="条" color="#ef5350" />
      </div>

      {/* AI 分析报告 */}
      {report?.ai_analysis && (
        <div style={{ ...styles.section, background: '#f0f7ff', borderLeft: '4px solid #1976d2' }}>
          <h3 style={{ ...styles.chartTitle, color: '#1976d2' }}>AI 分析建议</h3>
          <p style={{ fontSize: 14, color: '#333', lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>
            {report.ai_analysis}
          </p>
        </div>
      )}

      {/* 图表行 */}
      <div style={styles.chartRow}>
        <div style={styles.chartBox}>
          <h3 style={styles.chartTitle}>游客关注点分析</h3>
          <div ref={concernRef} style={{ width: '100%', height: 320 }} />
        </div>
        <div style={styles.chartBox}>
          <h3 style={styles.chartTitle}>每日服务与情感趋势</h3>
          <div ref={trendRef} style={{ width: '100%', height: 320 }} />
        </div>
      </div>

      {/* 热门提问 */}
      <div style={styles.section}>
        <h3 style={styles.chartTitle}>热门提问</h3>
        <table style={styles.table}>
          <thead>
            <tr><th style={styles.th}>#</th><th style={styles.th}>问题</th><th style={styles.th}>次数</th></tr>
          </thead>
          <tbody>
            {(report?.hot_questions || []).map((q: any, i: number) => (
              <tr key={i}>
                <td style={styles.td}>{i + 1}</td>
                <td style={{ ...styles.td, maxWidth: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{q.question}</td>
                <td style={styles.td}>{q.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 负面反馈 */}
      {report?.negative_samples?.length > 0 && (
        <div style={{ ...styles.section, borderLeft: '4px solid #ef5350' }}>
          <h3 style={{ ...styles.chartTitle, color: '#ef5350' }}>需关注的负面反馈</h3>
          {(report.negative_samples || []).map((n: any, i: number) => (
            <p key={i} style={{ fontSize: 13, color: '#666', padding: '6px 0', borderBottom: '1px solid #f0f0f0' }}>
              {n.content}
            </p>
          ))}
        </div>
      )}

      <div style={{ textAlign: 'right', paddingTop: 8 }}>
        <button onClick={fetchReport} style={styles.btn}>重新生成报告</button>
      </div>
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
      <div style={styles.section}>
        <h3 style={styles.chartTitle}>文档上传</h3>
        <p style={styles.hint}>支持 PDF / Word / TXT / Markdown，上传后自动分块向量化</p>
        <input type="file" accept=".pdf,.docx,.txt,.md" onChange={handleUpload} />
        {uploadMsg && <p style={styles.msg}>{uploadMsg}</p>}
      </div>

      <div style={styles.section}>
        <h3 style={styles.chartTitle}>FAQ 问答对导入</h3>
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

      <div style={styles.section}>
        <h3 style={styles.chartTitle}>已上传文档 ({docs.length})</h3>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>ID</th><th style={styles.th}>文件名</th><th style={styles.th}>类型</th>
              <th style={styles.th}>块数</th><th style={styles.th}>大小</th><th style={styles.th}>上传时间</th><th style={styles.th}>操作</th>
            </tr>
          </thead>
          <tbody>
            {docs.map((d: any) => (
              <tr key={d.id}>
                <td style={styles.td}>{d.id}</td><td style={styles.td}>{d.filename}</td><td style={styles.td}>{d.file_type}</td>
                <td style={styles.td}>{d.chunk_count}</td><td style={styles.td}>{Math.round(d.size_bytes / 1024)} KB</td>
                <td style={styles.td}>{d.uploaded_at}</td>
                <td style={styles.td}><button onClick={() => handleDelete(d.id)} style={styles.delBtn}>删除</button></td>
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
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const hot = await fetch(`${API}/admin/stats/qa-hot?limit=20`).then(r => r.json());
      setItems(hot || []);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  useEffect(() => { fetchData(); }, []);

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3 style={styles.chartTitle}>热门提问 Top 20</h3>
        <button onClick={fetchData} style={styles.btn}>刷新</button>
      </div>
      <table style={styles.table}>
        <thead>
          <tr><th style={styles.th}>#</th><th style={styles.th}>问题</th><th style={styles.th}>提问次数</th></tr>
        </thead>
        <tbody>
          {items.map((s: any, i: number) => (
            <tr key={i}>
              <td style={styles.td}>{i + 1}</td>
              <td style={{ ...styles.td, maxWidth: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.question}</td>
              <td style={styles.td}>{s.count}</td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr><td colSpan={3} style={{ ...styles.td, textAlign: 'center', color: '#999' }}>暂无对话记录</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

// ==================== 主面板 ====================
export default function AdminPanel() {
  const [tab, setTab] = useState<'dashboard' | 'report' | 'knowledge' | 'conversations'>('dashboard');

  const tabs = [
    { key: 'dashboard' as const, label: '数据大屏' },
    { key: 'report' as const, label: '感受度报告' },
    { key: 'knowledge' as const, label: '知识库管理' },
    { key: 'conversations' as const, label: '对话记录' },
  ];

  return (
    <div style={styles.panel}>
      <div style={styles.tabBar}>
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{ ...styles.tab, ...(tab === t.key ? styles.tabActive : {}) }}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div style={styles.tabContent}>
        {tab === 'dashboard' && <DashboardTab />}
        {tab === 'report' && <ReportTab />}
        {tab === 'knowledge' && <KnowledgeTab />}
        {tab === 'conversations' && <ConversationsTab />}
      </div>
    </div>
  );
}

// ==================== 样式 ====================
const styles: Record<string, React.CSSProperties> = {
  panel: { display: 'flex', flexDirection: 'column', height: '100%', background: '#f0f2f5', fontFamily: "'PingFang SC','Microsoft YaHei',sans-serif" },
  tabBar: { display: 'flex', gap: 0, background: '#fff', borderBottom: '2px solid #e8e8e8', padding: '0 24px' },
  tab: { padding: '14px 24px', border: 'none', background: 'transparent', fontSize: 15, cursor: 'pointer', color: '#666', borderBottom: '2px solid transparent', marginBottom: -2, transition: 'all 0.2s' },
  tabActive: { color: '#1976d2', borderBottomColor: '#1976d2', fontWeight: 600 },
  tabContent: { flex: 1, overflow: 'auto' },

  // Cards
  cardRow: { display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 16, marginBottom: 20 },
  card: { background: '#fff', borderRadius: 10, padding: 20, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' },
  cardTitle: { fontSize: 13, color: '#999', marginBottom: 8 },
  cardValue: { fontSize: 30, fontWeight: 700 },
  cardSub: { fontSize: 12, color: '#bbb', marginTop: 4 },

  // Charts
  chartRow: { display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16, marginBottom: 20 },
  chartBox: { background: '#fff', borderRadius: 10, padding: 20, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' },
  chartTitle: { fontSize: 15, fontWeight: 600, color: '#333', margin: '0 0 12px 0' },

  // Sections
  section: { background: '#fff', borderRadius: 10, padding: 20, marginBottom: 16, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' },
  reportHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 0 16px 0', marginBottom: 16, borderBottom: '1px solid #e8e8e8' },
  hint: { fontSize: 13, color: '#999', marginBottom: 12 },
  textarea: { width: '100%', maxWidth: 600, padding: 10, borderRadius: 6, border: '1px solid #ddd', fontSize: 13, fontFamily: 'monospace' },
  msg: { fontSize: 13, color: '#1976d2', marginTop: 8 },
  loading: { textAlign: 'center', padding: 60, color: '#999', fontSize: 15 },

  // Table
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: { textAlign: 'left', padding: '10px 12px', borderBottom: '2px solid #e8e8e8', color: '#666', fontWeight: 600, background: '#fafafa' },
  td: { padding: '10px 12px', borderBottom: '1px solid #f0f0f0', color: '#333' },

  // Buttons
  btn: { padding: '8px 20px', background: '#1976d2', color: '#fff', border: 'none', borderRadius: 6, fontSize: 14, cursor: 'pointer', fontWeight: 500 },
  delBtn: { padding: '4px 12px', background: '#ef5350', color: '#fff', border: 'none', borderRadius: 4, fontSize: 12, cursor: 'pointer' },
};
