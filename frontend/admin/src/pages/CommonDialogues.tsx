/**
 * 常用对话管理页 —— 增删改查 + 批量导入/导出（从 visitor 迁移）
 */
import { useState, useEffect, useCallback } from 'react';
import {
  getCommonDialogues,
  getCommonDialogueCategories,
  createCommonDialogue,
  updateCommonDialogue,
  deleteCommonDialogue,
  batchImportCommonDialogues,
  exportCommonDialogues,
  type CommonDialogue,
  type CommonDialogueCreate,
} from '../services/api';

const DEFAULT_FORM: CommonDialogueCreate = {
  question: '',
  answer: '',
  keywords: '',
  variants: '',
  category: '一般',
  priority: 0,
  enabled: 1,
};

export default function CommonDialogues() {
  const [dialogues, setDialogues] = useState<CommonDialogue[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [filterCategory, setFilterCategory] = useState('');
  const [filterEnabled, setFilterEnabled] = useState<number | undefined>(undefined);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);

  // 编辑弹窗
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<CommonDialogueCreate>({ ...DEFAULT_FORM });

  // 批量导入弹窗
  const [showImport, setShowImport] = useState(false);
  const [importJson, setImportJson] = useState('');

  // 删除确认
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [list, cats] = await Promise.all([
        getCommonDialogues({
          category: filterCategory || undefined,
          enabled: filterEnabled,
          search: search || undefined,
        }),
        getCommonDialogueCategories(),
      ]);
      setDialogues(list);
      setCategories(cats);
    } catch (e) {
      console.error('加载常用对话失败:', e);
    } finally {
      setLoading(false);
    }
  }, [filterCategory, filterEnabled, search]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const openCreate = () => {
    setEditingId(null);
    setForm({ ...DEFAULT_FORM });
    setShowForm(true);
  };

  const openEdit = (d: CommonDialogue) => {
    setEditingId(d.id);
    setForm({
      question: d.question,
      answer: d.answer,
      keywords: d.keywords,
      variants: (d as any).variants || '',
      category: d.category,
      priority: d.priority,
      enabled: d.enabled,
    });
    setShowForm(true);
  };

  const handleSubmit = async () => {
    if (!form.question.trim() || !form.answer.trim()) return;
    try {
      if (editingId) {
        await updateCommonDialogue(editingId, form);
      } else {
        await createCommonDialogue(form);
      }
      setShowForm(false);
      loadData();
    } catch (e) {
      console.error('保存失败:', e);
      alert('保存失败');
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteCommonDialogue(id);
      setDeleteId(null);
      loadData();
    } catch (e) {
      console.error('删除失败:', e);
    }
  };

  const handleToggle = async (d: CommonDialogue) => {
    try {
      await updateCommonDialogue(d.id, { enabled: d.enabled ? 0 : 1 });
      loadData();
    } catch (e) {
      console.error('切换失败:', e);
    }
  };

  const handleBatchImport = async () => {
    try {
      const items = JSON.parse(importJson);
      if (!Array.isArray(items)) {
        alert('请粘贴 JSON 数组格式的数据');
        return;
      }
      const result = await batchImportCommonDialogues(items);
      alert(`成功导入 ${result.imported} 条`);
      setShowImport(false);
      setImportJson('');
      loadData();
    } catch (e: any) {
      alert(`导入失败: ${e.message}`);
    }
  };

  const handleExport = async () => {
    try {
      const data = await exportCommonDialogues();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'common_dialogues.json';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('导出失败:', e);
    }
  };

  return (
    <div>
      <h1 style={styles.title}>💬 常用对话管理</h1>
      <p style={styles.subtitle}>管理预设问答，命中后直接返回预设回答，不经过 LLM 生成</p>

      {/* 工具栏 */}
      <div style={styles.toolbar}>
        <select
          value={filterCategory}
          onChange={e => setFilterCategory(e.target.value)}
          style={styles.select}
        >
          <option value="">全部分类</option>
          {categories.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <select
          value={filterEnabled === undefined ? '' : String(filterEnabled)}
          onChange={e => setFilterEnabled(e.target.value === '' ? undefined : Number(e.target.value))}
          style={styles.select}
        >
          <option value="">全部状态</option>
          <option value="1">已启用</option>
          <option value="0">已禁用</option>
        </select>
        <input
          type="text"
          placeholder="搜索问题/回答/关键词..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={styles.searchInput}
        />
        <div style={{ flex: 1 }} />
        <button onClick={openCreate} style={styles.primaryBtn}>＋ 新增</button>
        <button onClick={() => setShowImport(true)} style={styles.secondaryBtn}>📥 批量导入</button>
        <button onClick={handleExport} style={styles.secondaryBtn}>📤 导出全部</button>
      </div>

      {/* 列表 */}
      <div style={styles.tableWrap}>
        {loading ? (
          <div style={styles.empty}>加载中...</div>
        ) : dialogues.length === 0 ? (
          <div style={styles.empty}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>📭</div>
            <div>暂无常用对话数据</div>
          </div>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>问题</th>
                <th style={styles.th}>回答</th>
                <th style={styles.th}>分类</th>
                <th style={styles.th}>优先级</th>
                <th style={styles.th}>状态</th>
                <th style={styles.th}>更新时间</th>
                <th style={styles.th}>操作</th>
              </tr>
            </thead>
            <tbody>
              {dialogues.map(d => (
                <tr key={d.id} style={{ ...styles.tr, opacity: d.enabled ? 1 : 0.5 }}>
                  <td style={styles.td} title={d.question}>
                    {d.question.length > 30 ? d.question.slice(0, 30) + '...' : d.question}
                  </td>
                  <td style={styles.td} title={d.answer}>
                    {d.answer.length > 40 ? d.answer.slice(0, 40) + '...' : d.answer}
                  </td>
                  <td style={styles.td}>
                    <span style={styles.tag}>{d.category}</span>
                  </td>
                  <td style={styles.td}>{d.priority}</td>
                  <td style={styles.td}>
                    <button
                      onClick={() => handleToggle(d)}
                      style={{
                        ...styles.toggleBtn,
                        background: d.enabled ? '#C9A24E' : '#ccc',
                      }}
                    >
                      {d.enabled ? '启用' : '禁用'}
                    </button>
                  </td>
                  <td style={{ ...styles.td, fontSize: 12, color: '#8B7355' }}>
                    {d.updated_at ? new Date(d.updated_at).toLocaleString('zh-CN') : '-'}
                  </td>
                  <td style={styles.td}>
                    <button onClick={() => openEdit(d)} style={styles.actionBtn} title="编辑">✏️</button>
                    <button onClick={() => setDeleteId(d.id)} style={styles.actionBtn} title="删除">🗑️</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* 底部 */}
      <div style={styles.footer}>
        共 {dialogues.length} 条 | 已启用 {dialogues.filter(d => d.enabled).length} 条
      </div>

      {/* ====== 新增/编辑弹窗 ====== */}
      {showForm && (
        <div style={styles.modalOverlay} onClick={() => setShowForm(false)}>
          <div style={styles.modal} onClick={e => e.stopPropagation()}>
            <h3 style={{ margin: '0 0 20px', fontSize: 18 }}>{editingId ? '编辑常用对话' : '新增常用对话'}</h3>
            <div style={styles.formGroup}>
              <label style={styles.label}>触发问题 *</label>
              <input
                style={styles.textInput}
                value={form.question}
                onChange={e => setForm({ ...form, question: e.target.value })}
                placeholder="用户常问的问题"
              />
            </div>
            <div style={styles.formGroup}>
              <label style={styles.label}>预设回答 *</label>
              <textarea
                style={{ ...styles.textInput, minHeight: 80, resize: 'vertical' }}
                value={form.answer}
                onChange={e => setForm({ ...form, answer: e.target.value })}
                placeholder="预设的回答内容"
              />
            </div>
            <div style={styles.formGroup}>
              <label style={styles.label}>匹配关键词（逗号分隔）</label>
              <input
                style={styles.textInput}
                value={form.keywords}
                onChange={e => setForm({ ...form, keywords: e.target.value })}
                placeholder="如：门票,价格,多少钱"
              />
            </div>
            <div style={styles.formGroup}>
              <label style={styles.label}>相似提问变体（JSON数组，一行一个）</label>
              <textarea
                style={{ ...styles.textInput, minHeight: 80, resize: 'vertical', fontFamily: 'monospace', fontSize: 12 }}
                value={form.variants}
                onChange={e => setForm({ ...form, variants: e.target.value })}
                placeholder={'["几点开门", "开放时间是什么", "景区什么时候开门"]'}
              />
            </div>
            <div style={styles.formRow}>
              <div style={styles.formGroup}>
                <label style={styles.label}>分类</label>
                <input
                  style={styles.textInput}
                  value={form.category}
                  onChange={e => setForm({ ...form, category: e.target.value })}
                  placeholder="一般、票务、路线"
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>优先级</label>
                <input
                  type="number"
                  style={{ ...styles.textInput, width: 80 }}
                  value={form.priority}
                  onChange={e => setForm({ ...form, priority: Number(e.target.value) })}
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>启用</label>
                <select
                  style={styles.select}
                  value={String(form.enabled)}
                  onChange={e => setForm({ ...form, enabled: Number(e.target.value) })}
                >
                  <option value="1">是</option>
                  <option value="0">否</option>
                </select>
              </div>
            </div>
            <div style={styles.modalBtns}>
              <button onClick={() => setShowForm(false)} style={styles.secondaryBtn}>取消</button>
              <button onClick={handleSubmit} style={styles.primaryBtn}>
                {editingId ? '保存' : '创建'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ====== 批量导入弹窗 ====== */}
      {showImport && (
        <div style={styles.modalOverlay} onClick={() => setShowImport(false)}>
          <div style={styles.modal} onClick={e => e.stopPropagation()}>
            <h3 style={{ margin: '0 0 16px', fontSize: 18 }}>📥 批量导入常用对话</h3>
            <p style={{ fontSize: 13, color: '#8B7355', marginBottom: 12 }}>
              粘贴 JSON 数组，每项包含 question, answer, keywords, category, priority, enabled 字段：
            </p>
            <textarea
              style={{ ...styles.textInput, minHeight: 200, fontFamily: 'monospace', fontSize: 12, resize: 'vertical' }}
              value={importJson}
              onChange={e => setImportJson(e.target.value)}
              placeholder={`[\n  {\n    "question": "景区开放时间",\n    "answer": "景区每日8:00-17:30开放...",\n    "keywords": "开放,时间,几点",\n    "category": "一般",\n    "priority": 10,\n    "enabled": 1\n  }\n]`}
            />
            <div style={styles.modalBtns}>
              <button onClick={() => setShowImport(false)} style={styles.secondaryBtn}>取消</button>
              <button onClick={handleBatchImport} style={styles.primaryBtn}>导入</button>
            </div>
          </div>
        </div>
      )}

      {/* ====== 删除确认 ====== */}
      {deleteId !== null && (
        <div style={styles.modalOverlay} onClick={() => setDeleteId(null)}>
          <div style={{ ...styles.modal, maxWidth: 380 }} onClick={e => e.stopPropagation()}>
            <h3 style={{ margin: '0 0 12px', fontSize: 18 }}>确认删除</h3>
            <p style={{ fontSize: 14, color: '#8B7355', lineHeight: 1.6 }}>确定要删除这条常用对话吗？此操作不可恢复。</p>
            <div style={styles.modalBtns}>
              <button onClick={() => setDeleteId(null)} style={styles.secondaryBtn}>取消</button>
              <button onClick={() => handleDelete(deleteId)} style={{ ...styles.primaryBtn, background: '#c0392b' }}>
                确认删除
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  title: {
    fontSize: 22,
    fontWeight: 600,
    marginBottom: 4,
    color: '#4A3028',
  },
  subtitle: {
    fontSize: 13,
    color: '#8B7355',
    marginBottom: 20,
  },
  toolbar: {
    display: 'flex',
    gap: 10,
    marginBottom: 16,
    alignItems: 'center',
    flexWrap: 'wrap' as const,
    background: '#fff',
    padding: '12px 16px',
    borderRadius: 10,
    boxShadow: '0 1px 4px rgba(74,48,40,0.06)',
  },
  select: {
    padding: '7px 12px',
    borderRadius: 6,
    border: '1px solid #E0D3C0',
    fontSize: 13,
    outline: 'none',
    background: '#fff',
  },
  searchInput: {
    padding: '7px 14px',
    borderRadius: 6,
    border: '1px solid #E0D3C0',
    fontSize: 13,
    outline: 'none',
    width: 240,
  },
  primaryBtn: {
    padding: '7px 18px',
    borderRadius: 6,
    border: 'none',
    background: '#B8860B',
    color: '#fff',
    fontSize: 13,
    cursor: 'pointer',
    fontWeight: 500,
  },
  secondaryBtn: {
    padding: '7px 18px',
    borderRadius: 6,
    border: '1px solid #E0D3C0',
    background: '#fff',
    color: '#4A3028',
    fontSize: 13,
    cursor: 'pointer',
  },
  tableWrap: {
    background: '#fff',
    borderRadius: 10,
    boxShadow: '0 1px 4px rgba(74,48,40,0.06)',
    overflow: 'auto',
  },
  empty: {
    textAlign: 'center',
    padding: 60,
    color: '#8B7355',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
  },
  th: {
    textAlign: 'left' as const,
    padding: '12px 14px',
    borderBottom: '2px solid #E0D3C0',
    fontSize: 13,
    color: '#8B7355',
    fontWeight: 600,
    background: '#FFF9ED',
    whiteSpace: 'nowrap' as const,
  },
  tr: {
    borderBottom: '1px solid #E0D3C0',
  },
  td: {
    padding: '12px 14px',
    fontSize: 13,
    color: '#4A3028',
    verticalAlign: 'middle' as const,
  },
  tag: {
    display: 'inline-block',
    padding: '2px 10px',
    borderRadius: 4,
    background: '#e3f2fd',
    color: '#B8860B',
    fontSize: 12,
    fontWeight: 500,
  },
  toggleBtn: {
    padding: '3px 12px',
    borderRadius: 4,
    border: 'none',
    color: '#fff',
    fontSize: 12,
    cursor: 'pointer',
    fontWeight: 500,
  },
  actionBtn: {
    padding: '4px 8px',
    borderRadius: 4,
    border: 'none',
    background: 'transparent',
    cursor: 'pointer',
    fontSize: 16,
  },
  footer: {
    marginTop: 12,
    fontSize: 13,
    color: '#8B7355',
  },
  // 弹窗
  modalOverlay: {
    position: 'fixed' as const,
    inset: 0,
    zIndex: 1100,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'rgba(74,48,40,0.35)',
  },
  modal: {
    width: '90%',
    maxWidth: 560,
    background: '#fff',
    borderRadius: 12,
    padding: 28,
    boxShadow: '0 12px 48px rgba(74,48,40,0.18)',
  },
  formGroup: {
    marginBottom: 14,
    flex: 1,
  },
  formRow: {
    display: 'flex',
    gap: 12,
  },
  label: {
    display: 'block',
    fontSize: 13,
    color: '#555',
    marginBottom: 5,
    fontWeight: 500,
  },
  textInput: {
    width: '100%',
    padding: '9px 14px',
    borderRadius: 6,
    border: '1px solid #E0D3C0',
    fontSize: 14,
    outline: 'none',
    boxSizing: 'border-box' as any,
  },
  modalBtns: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: 10,
    marginTop: 20,
  },
};
