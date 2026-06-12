/**
 * 景区导览后台管理 —— 游客分析全模块
 * 交互指标/景点热度/服务质量/时间对比/高频提问/游客分层/情感分析
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import * as echarts from 'echarts';

const API = '/api/admin';

// ============ 通用组件 ============
function StatCard({ title, value, sub, color }: { title: string; value: any; sub?: string; color: string }) {
  return <div style={s.card}>
    <div style={s.cardTitle}>{title}</div>
    <div style={{ ...s.cardValue, color }}>{value}</div>
    {sub && <div style={s.cardSub}>{sub}</div>}
  </div>;
}

function SectionBox({ title, children }: { title: string; children: React.ReactNode }) {
  return <div style={s.section}>
    <h3 style={s.chartTitle}>{title}</h3>
    {children}
  </div>;
}

function useChart(ref: React.RefObject<HTMLDivElement>, option: any, deps: any[]) {
  useEffect(() => {
    if (!ref.current) return;
    const c = echarts.init(ref.current);
    c.setOption(option, true);
    const onResize = () => c.resize();
    window.addEventListener('resize', onResize);
    return () => { window.removeEventListener('resize', onResize); c.dispose(); };
  }, deps);
}

// ============ 数据大屏 Tab ============
function DashboardTab() {
  const [data, setData] = useState<any>(null);
  const trendRef = useRef<HTMLDivElement>(null);
  const pieRef = useRef<HTMLDivElement>(null);
  const hourRef = useRef<HTMLDivElement>(null);

  const loadData = useCallback(async () => {
    const r = await (await window.fetch(`${API}/analytics/full-dashboard`)).json();
    setData(r);
  }, []);

  useEffect(() => { loadData(); }, []);

  // 时段热力图
  useChart(hourRef, {
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', top: '5%', bottom: '5%', containLabel: true },
    xAxis: { type: 'category', data: (data?.interaction?.hourly_distribution || []).map((h: any) => h.hour + '时'), axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: (data?.interaction?.hourly_distribution || []).map((h: any) => h.count), itemStyle: { color: '#1976d2', borderRadius: 2 } }],
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

  // 本周趋势
  useChart(trendRef, {
    tooltip: { trigger: 'axis' },
    legend: { data: ['对话数', '满意度%'], bottom: 0 },
    grid: { left: '3%', right: '6%', bottom: '12%', top: '5%', containLabel: true },
    xAxis: { type: 'category', data: (data?.time_comparison?.week_daily || []).map((_: any, i: number) => ['一','二','三','四','五','六','日'][i]) },
    yAxis: [{ type: 'value', name: '条' }, { type: 'value', name: '%', min: 0, max: 100 }],
    series: [
      { name: '对话数', type: 'bar', data: (data?.time_comparison?.week_daily || []).map((d: any) => d.conversations), itemStyle: { color: '#90caf9', borderRadius: 4 }, barWidth: '40%' },
      { name: '满意度%', type: 'line', yAxisIndex: 1, data: (data?.time_comparison?.week_daily || []).map((d: any) => d.rate), smooth: true, itemStyle: { color: '#66bb6a' }, lineStyle: { width: 3 } },
    ],
  }, [data]);

  const inter = data?.interaction || {};
  const qa = data?.qa_quality || {};
  const comp = data?.time_comparison || {};

  return (
    <div style={{ padding: 20 }}>
      {/* 核心指标 */}
      <div style={s.row4}>
        <StatCard title="今日服务人次" value={inter.today?.sessions || 0} sub={`昨日 ${inter.yesterday?.sessions || 0}`} color="#1976d2" />
        <StatCard title="今日对话数" value={inter.today?.conversations || 0} sub={`昨日 ${inter.yesterday?.conversations || 0}`} color="#43a047" />
        <StatCard title="本周服务人次" value={inter.week?.sessions || 0} sub={`月度 ${inter.month?.sessions || 0}`} color="#ff8f00" />
        <StatCard title="回访游客(周)" value={inter.repeat_visitors_week || 0} sub={`满意度 ${qa.satisfaction_rate || 0}%`} color="#7e57c2" />
      </div>

      {/* 图表 */}
      <div style={s.row2}>
        <SectionBox title="本周趋势（对话量 + 满意度）">
          <div ref={trendRef} style={{ height: 300 }} />
        </SectionBox>
        <SectionBox title="情感分布总览">
          <div ref={pieRef} style={{ height: 300 }} />
        </SectionBox>
      </div>

      <div style={s.row2}>
        <SectionBox title="全天交互时段分布">
          <div ref={hourRef} style={{ height: 280 }} />
        </SectionBox>
        <SectionBox title="AI服务质量">
          <div style={{ padding: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-around', textAlign: 'center' }}>
              <div><div style={{ fontSize: 28, fontWeight: 700, color: '#43a047' }}>{qa.satisfaction_rate || 0}%</div><div style={{ fontSize: 12, color: '#999' }}>满意度</div></div>
              <div><div style={{ fontSize: 28, fontWeight: 700, color: '#ef5350' }}>{qa.unable_rate || 0}%</div><div style={{ fontSize: 12, color: '#999' }}>答不上率</div></div>
              <div><div style={{ fontSize: 28, fontWeight: 700, color: '#1976d2' }}>{qa.total_answers || 0}</div><div style={{ fontSize: 12, color: '#999' }}>总回答数</div></div>
            </div>
            <div style={{ marginTop: 12, fontSize: 12, color: '#999' }}>
              周环比: {comp.week_change > 0 ? '+' : ''}{comp.week_change || 0}%
            </div>
          </div>
        </SectionBox>
      </div>

      <div style={{ textAlign: 'right', paddingTop: 8 }}>
        <button onClick={loadData} style={s.btn}>刷新数据</button>
      </div>
    </div>
  );
}

// ============ 景点热度 Tab ============
function SpotsTab() {
  const [data, setData] = useState<any>(null);
  const barRef = useRef<HTMLDivElement>(null);

  const loadData = useCallback(async () => {
    const r = await (await fetch(`${API}/analytics/spot-popularity`)).json();
    setData(r);
  }, []);

  useEffect(() => { loadData(); }, []);

  useChart(barRef, {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '5%', right: '8%', top: '5%', bottom: '5%', containLabel: true },
    xAxis: { type: 'value', name: '咨询次数' },
    yAxis: { type: 'category', data: (data?.ranking || []).map((s: any) => s.name).reverse(), inverse: true },
    series: [{
      type: 'bar', data: (data?.ranking || []).map((s: any) => s.count).reverse(),
      itemStyle: { color: '#ff8f00', borderRadius: [0, 4, 4, 0] },
      label: { show: true, position: 'right', fontSize: 12 },
    }],
  }, [data]);

  return (
    <div style={{ padding: 20 }}>
      <div style={s.row2}>
        <SectionBox title="景点问询热度排行（基于近30天关键词匹配）">
          <div ref={barRef} style={{ height: 360 }} />
        </SectionBox>
        <div>
          <SectionBox title="TOP5 热门景点">
            {(data?.top5 || []).map((spot: any, i: number) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}>
                <span>{i + 1}. {spot.name}</span>
                <span style={{ fontWeight: 600, color: '#ff8f00' }}>{spot.count} 次</span>
              </div>
            ))}
          </SectionBox>
          <SectionBox title="待关注冷门景点">
            {(data?.cold_spots || []).length > 0 ? (
              (data?.cold_spots || []).slice(0, 5).map((s: any, i: number) => (
                <div key={i} style={{ padding: '4px 0', color: '#999' }}>{s.name}</div>
              ))
            ) : <div style={{ color: '#999' }}>所有景点均有问询记录</div>}
          </SectionBox>
        </div>
      </div>
      <button onClick={loadData} style={s.btn}>刷新</button>
    </div>
  );
}

// ============ 时间对比 Tab ============
function TimeCompareTab() {
  const [data, setData] = useState<any>(null);
  const lineRef = useRef<HTMLDivElement>(null);

  const loadData = useCallback(async () => {
    const r = await (await fetch(`${API}/analytics/time-comparison`)).json();
    setData(r);
  }, []);

  useEffect(() => { loadData(); }, []);

  useChart(lineRef, {
    tooltip: { trigger: 'axis' },
    legend: { data: ['对话数', '满意度%'], bottom: 0 },
    grid: { left: '3%', right: '6%', bottom: '12%', top: '5%', containLabel: true },
    xAxis: { type: 'category', data: (data?.week_daily || []).map((_: any, i: number) => ['一','二','三','四','五','六','日'][i]) },
    yAxis: [{ type: 'value' }, { type: 'value', name: '%', min: 0, max: 100 }],
    series: [
      { name: '对话数', type: 'bar', data: (data?.week_daily || []).map((d: any) => d.conversations), itemStyle: { color: '#1976d2', borderRadius: 4 }, barWidth: '40%' },
      { name: '满意度%', type: 'line', yAxisIndex: 1, data: (data?.week_daily || []).map((d: any) => d.rate), smooth: true, itemStyle: { color: '#43a047' }, lineStyle: { width: 3 } },
    ],
  }, [data]);

  const td = data?.today || {};
  const yd = data?.yesterday || {};

  return (
    <div style={{ padding: 20 }}>
      <div style={s.row4}>
        <StatCard title="今日对话" value={td.conversations || 0} sub={`满意度 ${td.rate || 0}%`} color="#1976d2" />
        <StatCard title="昨日对话" value={yd.conversations || 0} sub={`满意度 ${yd.rate || 0}%`} color="#42a5f5" />
        <StatCard title="本周总计" value={data?.this_week_total || 0} sub={`上周 ${data?.last_week_total || 0}`} color="#ff8f00" />
        <StatCard title="周环比" value={(data?.week_change > 0 ? '+' : '') + (data?.week_change || 0) + '%'} sub="对话量变化" color={data?.week_change >= 0 ? '#43a047' : '#ef5350'} />
      </div>
      <div style={s.row1}>
        <SectionBox title="本周每日趋势">
          <div ref={lineRef} style={{ height: 320 }} />
        </SectionBox>
      </div>
      <button onClick={loadData} style={s.btn}>刷新</button>
    </div>
  );
}

// ============ 问答分析 Tab ============
function QATab() {
  const [data, setData] = useState<any>(null);
  const catRef = useRef<HTMLDivElement>(null);

  const loadData = useCallback(async () => {
    const [qa, qAnalysis] = await Promise.all([
      fetch(`${API}/analytics/qa-quality`).then(r => r.json()),
      fetch(`${API}/analytics/question-analysis`).then(r => r.json()),
    ]);
    setData({ qa, qAnalysis });
  }, []);

  useEffect(() => { loadData(); }, []);

  useChart(catRef, {
    tooltip: { trigger: 'item', formatter: '{b}: {c}次 ({d}%)' },
    legend: { bottom: 0, textStyle: { fontSize: 10 } },
    series: [{
      type: 'pie', radius: ['40%', '65%'], center: ['50%', '43%'],
      label: { formatter: '{b}\n{d}%', fontSize: 10 },
      data: (data?.qAnalysis?.category_distribution || []).map((c: any) => ({
        value: c.count, name: c.category,
        itemStyle: { color: ['#1976d2','#43a047','#ff8f00','#e53935','#7e57c2','#00acc1','#ff7043'][['门票价格','交通停车','景点历史文化','游玩路线','餐饮住宿','演出时间','设施服务'].indexOf(c.category)] || '#999' },
      })),
    }],
  }, [data]);

  const qa = data?.qa || {};
  const qa2 = data?.qAnalysis || {};

  return (
    <div style={{ padding: 20 }}>
      <div style={s.row4}>
        <StatCard title="满意度" value={(qa.satisfaction_rate || 0) + '%'} sub={`正面 ${qa.sentiment?.positive || 0}`} color="#43a047" />
        <StatCard title="答不上率" value={(qa.unable_rate || 0) + '%'} sub={`${qa.unable_to_answer || 0} 条`} color="#ef5350" />
        <StatCard title="总回答数" value={qa.total_answers || 0} sub="近30天" color="#1976d2" />
        <StatCard title="无法解答问题" value={qa2.unable_to_answer_count || 0} sub="待补充知识库" color="#ff8f00" />
      </div>
      <div style={s.row2}>
        <SectionBox title="提问分类占比">
          <div ref={catRef} style={{ height: 340 }} />
        </SectionBox>
        <div>
          <SectionBox title="高频问题 TOP10">
            {(qa2.top_questions || []).slice(0, 10).map((q: any, i: number) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid #f0f0f0', fontSize: 12 }}>
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginRight: 8 }}>{i + 1}. {q.question}</span>
                <span style={{ fontWeight: 600 }}>{q.count}次</span>
              </div>
            ))}
          </SectionBox>
        </div>
      </div>
      <SectionBox title="待补充：AI无法准确回复的问题">
        {(qa2.unable_questions || []).slice(0, 8).map((q: string, i: number) => (
          <div key={i} style={{ padding: '6px 0', borderBottom: '1px solid #f0f0f0', fontSize: 12, color: '#ef5350' }}>{q}</div>
        ))}
        {(!qa2.unable_questions || qa2.unable_questions.length === 0) && <div style={{ color: '#999', fontSize: 12 }}>暂无无法回复的问题</div>}
      </SectionBox>
      <button onClick={loadData} style={{ ...s.btn, marginTop: 12 }}>刷新</button>
    </div>
  );
}

// ============ 游客分层 Tab ============
function VisitorTab() {
  const [data, setData] = useState<any>(null);
  const tagRef = useRef<HTMLDivElement>(null);
  const prefRef = useRef<HTMLDivElement>(null);

  const loadData = useCallback(async () => {
    const r = await (await fetch(`${API}/analytics/visitor-segmentation`)).json();
    setData(r);
  }, []);

  useEffect(() => { loadData(); }, []);

  useChart(tagRef, {
    tooltip: { trigger: 'item', formatter: '{b}: {c}人 ({d}%)' },
    series: [{
      type: 'pie', radius: ['40%', '65%'], center: ['50%', '43%'],
      data: (data?.tags || []).map((t: any, i: number) => ({
        value: t.count, name: t.tag,
        itemStyle: { color: ['#42a5f5','#66bb6a','#ffa726','#ef5350','#ab47bc','#26c6da'][i] || '#999' },
      })),
    }],
  }, [data]);

  useChart(prefRef, {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie', radius: ['40%', '65%'], center: ['50%', '43%'],
      label: { formatter: '{b}\n{d}%' },
      data: (data?.preferences || []).map((p: any, i: number) => ({
        value: p.count, name: p.preference,
        itemStyle: { color: ['#43a047','#ff8f00','#ef5350','#7e57c2'][i] || '#999' },
      })),
    }],
  }, [data]);

  const seg = data?.segments || {};
  const total = data?.total_visitors || 1;

  return (
    <div style={{ padding: 20 }}>
      <div style={s.row4}>
        <StatCard title="总游客数" value={total} sub="近30天" color="#1976d2" />
        <StatCard title="首次到访" value={seg.single_visit || 0} sub={Math.round((seg.single_visit || 0) / total * 100) + '%'} color="#43a047" />
        <StatCard title="多次回访" value={seg.multi_visit || 0} sub={Math.round((seg.multi_visit || 0) / total * 100) + '%'} color="#ff8f00" />
        <StatCard title="高频复访" value={seg.heavy_visit || 0} sub={Math.round((seg.heavy_visit || 0) / total * 100) + '%'} color="#7e57c2" />
      </div>
      <div style={s.row2}>
        <SectionBox title="游客群体标签分布">
          <div ref={tagRef} style={{ height: 320 }} />
        </SectionBox>
        <SectionBox title="游玩偏好统计">
          <div ref={prefRef} style={{ height: 320 }} />
        </SectionBox>
      </div>
      <button onClick={loadData} style={s.btn}>刷新</button>
    </div>
  );
}

// ============ 负面反馈 Tab ============
function NegativeTab() {
  const [data, setData] = useState<any>(null);
  const barRef = useRef<HTMLDivElement>(null);

  const loadData = useCallback(async () => {
    const r = await (await fetch(`${API}/analytics/negative-analysis`)).json();
    setData(r);
  }, []);

  useEffect(() => { loadData(); }, []);

  useChart(barRef, {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '8%', top: '5%', bottom: '5%', containLabel: true },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: (data?.categories || []).map((c: any) => c.category).reverse(), inverse: true },
    series: [{
      type: 'bar', data: (data?.categories || []).map((c: any) => c.count).reverse(),
      itemStyle: { color: '#ef5350', borderRadius: [0, 4, 4, 0] },
      label: { show: true, position: 'right' },
    }],
  }, [data]);

  return (
    <div style={{ padding: 20 }}>
      <div style={s.row2}>
        <SectionBox title="负面反馈分类统计">
          <div ref={barRef} style={{ height: 340 }} />
        </SectionBox>
        <div>
          <SectionBox title="负面反馈样本">
            {(data?.samples || []).slice(0, 10).map((sample: string, i: number) => (
              <div key={i} style={{ padding: '6px 0', borderBottom: '1px solid #f0f0f0', fontSize: 12, color: '#666' }}>{sample}</div>
            ))}
          </SectionBox>
          {data?.ai_suggestion && (
            <div style={{ ...s.section, background: '#fff3e0', borderLeft: '4px solid #ff8f00', marginTop: 16 }}>
              <h4 style={{ margin: '0 0 8px 0', fontSize: 14, color: '#e65100' }}>AI 优化建议</h4>
              <p style={{ fontSize: 13, color: '#333', lineHeight: 1.8 }}>{data.ai_suggestion}</p>
            </div>
          )}
        </div>
      </div>
      <button onClick={loadData} style={s.btn}>刷新</button>
    </div>
  );
}

// ============ 知识库管理 (保留原有) ============
function KnowledgeTab() {
  const [docs, setDocs] = useState<any[]>([]);
  const [faqCount, setFaqCount] = useState(0);
  const [uploadMsg, setUploadMsg] = useState('');
  const [faqMsg, setFaqMsg] = useState('');
  const [faqJson, setFaqJson] = useState('');

  const fetchDocs = async () => {
    const [d, f] = await Promise.all([
      fetch('/api/rag/admin/documents').then(r => r.json()),
      fetch('/api/rag/health').then(r => r.json()),
    ]);
    setDocs(d.documents || []);
    setFaqCount(f.stats?.faq_pairs || 0);
  };

  useEffect(() => { fetchDocs(); }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadMsg('上传中...');
    const form = new FormData(); form.append('file', file);
    const resp = await fetch('/api/rag/admin/upload', { method: 'POST', body: form });
    const data = await resp.json();
    setUploadMsg(data.message || '上传成功');
    fetchDocs();
  };

  const handleFaqImport = async () => {
    if (!faqJson.trim()) return;
    setFaqMsg('导入中...');
    const pairs = JSON.parse(faqJson);
    const resp = await fetch('/api/rag/admin/faq/import', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ faq_pairs: pairs }),
    });
    setFaqMsg((await resp.json()).message || '导入成功');
    setFaqJson('');
    fetchDocs();
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确定删除？')) return;
    await fetch(`/api/rag/admin/documents/${id}`, { method: 'DELETE' });
    fetchDocs();
  };

  return (
    <div style={{ padding: 20 }}>
      <SectionBox title="文档上传">
        <p style={s.hint}>PDF / Word / TXT / Markdown，上传后自动分块向量化</p>
        <input type="file" accept=".pdf,.docx,.txt,.md" onChange={handleUpload} />
        {uploadMsg && <p style={{ color: '#1976d2', fontSize: 13 }}>{uploadMsg}</p>}
      </SectionBox>
      <SectionBox title={`FAQ 导入（当前 ${faqCount} 条）`}>
        <textarea value={faqJson} onChange={e => setFaqJson(e.target.value)} placeholder={`[{"question":"...","answer":"..."}]`} style={s.textarea} rows={5} />
        <br /><button onClick={handleFaqImport} style={{ ...s.btn, marginTop: 8 }}>导入 FAQ</button>
        {faqMsg && <p style={{ color: '#1976d2', fontSize: 13 }}>{faqMsg}</p>}
      </SectionBox>
      <SectionBox title={`已上传文档 (${docs.length})`}>
        <table style={s.table}>
          <thead><tr>{['ID','文件名','类型','块数','大小','上传时间','操作'].map(h => <th key={h} style={s.th}>{h}</th>)}</tr></thead>
          <tbody>
            {docs.map((d: any) => (
              <tr key={d.id}>
                <td style={s.td}>{d.id}</td><td style={s.td}>{d.filename}</td><td style={s.td}>{d.file_type}</td>
                <td style={s.td}>{d.chunk_count}</td><td style={s.td}>{Math.round(d.size_bytes / 1024)} KB</td>
                <td style={s.td}>{d.uploaded_at}</td>
                <td style={s.td}><button onClick={() => handleDelete(d.id)} style={s.delBtn}>删除</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </SectionBox>
    </div>
  );
}

// ============ 主面板 ============
export default function AdminPanel() {
  const tabs = [
    { key: 'dashboard', label: '数据大屏' },
    { key: 'spots', label: '景点热度' },
    { key: 'compare', label: '时间对比' },
    { key: 'qa', label: '问答分析' },
    { key: 'visitor', label: '游客分层' },
    { key: 'negative', label: '负面反馈' },
    { key: 'knowledge', label: '知识库' },
  ] as const;
  const [tab, setTab] = useState<typeof tabs[number]['key']>('dashboard');

  return (
    <div style={s.panel}>
      <div style={s.tabBar}>
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)} style={{ ...s.tab, ...(tab === t.key ? s.tabActive : {}) }}>
            {t.label}
          </button>
        ))}
      </div>
      <div style={{ flex: 1, overflow: 'auto' }}>
        {tab === 'dashboard' && <DashboardTab />}
        {tab === 'spots' && <SpotsTab />}
        {tab === 'compare' && <TimeCompareTab />}
        {tab === 'qa' && <QATab />}
        {tab === 'visitor' && <VisitorTab />}
        {tab === 'negative' && <NegativeTab />}
        {tab === 'knowledge' && <KnowledgeTab />}
      </div>
    </div>
  );
}

// ============ 样式 ============
const s: Record<string, React.CSSProperties> = {
  panel: { display: 'flex', flexDirection: 'column', height: '100%', background: '#f0f2f5', fontFamily: "'PingFang SC','Microsoft YaHei',sans-serif" },
  tabBar: { display: 'flex', background: '#fff', borderBottom: '2px solid #e8e8e8', padding: '0 20px', flexShrink: 0, overflowX: 'auto' },
  tab: { padding: '12px 20px', border: 'none', background: 'transparent', fontSize: 14, cursor: 'pointer', color: '#666', borderBottom: '2px solid transparent', marginBottom: -2, whiteSpace: 'nowrap', transition: 'all 0.2s' },
  tabActive: { color: '#1976d2', borderBottomColor: '#1976d2', fontWeight: 600 },
  row4: { display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14, marginBottom: 18 },
  row2: { display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 14, marginBottom: 18 },
  row1: { marginBottom: 18 },
  card: { background: '#fff', borderRadius: 10, padding: 18, boxShadow: '0 1px 4px rgba(0,0,0,0.05)' },
  cardTitle: { fontSize: 13, color: '#999', marginBottom: 6 },
  cardValue: { fontSize: 28, fontWeight: 700 },
  cardSub: { fontSize: 11, color: '#bbb', marginTop: 4 },
  section: { background: '#fff', borderRadius: 10, padding: 18, marginBottom: 14, boxShadow: '0 1px 4px rgba(0,0,0,0.05)' },
  chartTitle: { fontSize: 15, fontWeight: 600, color: '#333', margin: '0 0 12px 0' },
  hint: { fontSize: 12, color: '#999', marginBottom: 10 },
  textarea: { width: '100%', maxWidth: 600, padding: 10, borderRadius: 6, border: '1px solid #ddd', fontSize: 13, fontFamily: 'monospace' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 12 },
  th: { textAlign: 'left', padding: '8px 10px', borderBottom: '2px solid #e8e8e8', color: '#666', fontWeight: 600, background: '#fafafa' },
  td: { padding: '8px 10px', borderBottom: '1px solid #f0f0f0', color: '#333' },
  btn: { padding: '8px 20px', background: '#1976d2', color: '#fff', border: 'none', borderRadius: 6, fontSize: 13, cursor: 'pointer', fontWeight: 500 },
  delBtn: { padding: '3px 10px', background: '#ef5350', color: '#fff', border: 'none', borderRadius: 4, fontSize: 11, cursor: 'pointer' },
};
