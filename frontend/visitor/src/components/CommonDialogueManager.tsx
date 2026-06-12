/**
 * 常用对话管理面板 —— 增删改查 + 批量导入/导出。
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

interface Props {
  onClose: () => void;
}

const DEFAULT_FORM: CommonDialogueCreate = {
  question: '',
  answer: '',
  keywords: '',
  category: '一般',
  priority: 0,
  enabled: 1,
};

export default function CommonDialogueManager({ onClose }: Props) {
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

  // 打开新增表单
  const openCreate = () => {
    setEditingId(null);
    setForm({ ...DEFAULT_FORM });
    setShowForm(true);
  };

  // 打开编辑表单
  const openEdit = (d: CommonDialogue) => {
    setEditingId(d.id);
    setForm({
      question: d.question,
      answer: d.answer,
      keywords: d.keywords,
      category: d.category,
      priority: d.priority,
      enabled: d.enabled,
    });
    setShowForm(true);
  };

  // 提交表单
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
    }
  };

  // 删除
  const handleDelete = async (id: number) => {
    try {
      await deleteCommonDialogue(id);
      setDeleteId(null);
      loadData();
    } catch (e) {
      console.error('删除失败:', e);
    }
  };

  // 切换启用
  const handleToggle = async (d: CommonDialogue) => {
    try {
      await updateCommonDialogue(d.id, { enabled: d.enabled ? 0 : 1 });
      loadData();
    } catch (e) {
      console.error('切换失败:', e);
    }
  };

  // 批量导入
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

  // 导出
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
    <div style={styles.overlay}>
      <div style={styles.panel}>
        {/* 头部 */}
        <div style={styles.header}>
          <h2 style={styles.title}>📋 常用对话管理</h2>
          <button onClick={onClose} style={styles.closeBtn}>✕</button>
        </div>

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
            placeholder="搜索..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={styles.searchInput}
          />
          <div style={{ flex: 1 }} />
          <button onClick={openCreate} style={styles.primaryBtn}>＋ 新增</button>
          <button onClick={() => setShowImport(true)} style={styles.secondaryBtn}>📥 批量导入</button>
          <button onClick={handleExport} style={styles.secondaryBtn}>📤 导出</button>
        </div>

        {/* 列表 */}
        <div style={styles.list}>
          {loading ? (
            <div style={styles.empty}>加载中...</div>
          ) : dialogues.length === 0 ? (
            <div style={styles.empty}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>📭</div>
              <div>暂无常用对话</div>
              <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                点击「新增」创建，或「批量导入」导入数据
              </div>
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
                  <th style={styles.th}>操作</th>
                </tr>
              </thead>
              <tbody>
                {dialogues.map(d => (
                  <tr key={d.id} style={{
                    ...styles.tr,
                    opacity: d.enabled ? 1 : 0.5,
                  }}>
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
                          background: d.enabled ? '#4CAF50' : '#ccc',
                        }}
                      >
                        {d.enabled ? '启用' : '禁用'}
                      </button>
                    </td>
                    <td style={styles.td}>
                      <button onClick={() => openEdit(d)} style={styles.actionBtn}>✏️</button>
                      <button onClick={() => setDeleteId(d.id)} style={styles.actionBtn}>🗑️</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* 底部统计 */}
        <div style={styles.footer}>
          共 {dialogues.length} 条 | 已启用 {dialogues.filter(d => d.enabled).length} 条
        </div>
      </div>

      {/* ====== 新增/编辑弹窗 ====== */}
      {showForm && (
        <div style={styles.modalOverlay} onClick={() => setShowForm(false)}>
          <div style={styles.modal} onClick={e => e.stopPropagation()}>
            <h3 style={{ margin: '0 0 16px' }}>{editingId ? '编辑常用对话' : '新增常用对话'}</h3>
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
            <div style={styles.formRow}>
              <div style={styles.formGroup}>
                <label style={styles.label}>分类</label>
                <input
                  style={styles.textInput}
                  value={form.category}
                  onChange={e => setForm({ ...form, category: e.target.value })}
                  placeholder="如：一般、票务、路线"
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
            <h3 style={{ margin: '0 0 16px' }}>📥 批量导入常用对话</h3>
            <p style={{ fontSize: 13, color: '#666', marginBottom: 8 }}>
              粘贴 JSON 数组，每项包含 question, answer, keywords, category, priority, enabled 字段：
            </p>
            <textarea
              style={{ ...styles.textInput, minHeight: 200, fontFamily: 'monospace', fontSize: 12, resize: 'vertical' }}
              value={importJson}
              onChange={e => setImportJson(e.target.value)}
              placeholder={`[
  {
    "question": "景区开放时间",
    "answer": "景区每日8:00-17:30开放...",
    "keywords": "开放,时间,几点",
    "category": "一般",
    "priority": 10,
    "enabled": 1
  }
]`}
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
          <div style={{ ...styles.modal, maxWidth: 360 }} onClick={e => e.stopPropagation()}>
            <h3 style={{ margin: '0 0 12px' }}>确认删除</h3>
            <p style={{ fontSize: 14, color: '#666' }}>确定要删除这条常用对话吗？此操作不可恢复。</p>
            <div style={styles.modalBtns}>
              <button onClick={() => setDeleteId(null)} style={styles.secondaryBtn}>取消</button>
              <button onClick={() => handleDelete(deleteId)} style={{ ...styles.primaryBtn, background: '#ff4d4f' }}>
                确认删除
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ==================== 样式 ====================

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'fixed',
    inset: 0,
    zIndex: 1000,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'rgba(0,0,0,0.4)',
  },
  panel: {
    width: '90%',
    maxWidth: 1000,
    height: '80%',
    maxHeight: 700,
    background: '#fff',
    borderRadius: 12,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    boxShadow: '0 8px 32px rgba(0,0,0,0.15)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 20px',
    borderBottom: '1px solid #eee',
  },
  title: {
    margin: 0,
    fontSize: 18,
    fontWeight: 600,
  },
  closeBtn: {
    width: 32,
    height: 32,
    borderRadius: '50%',
    border: 'none',
    background: '#f0f0f0',
    cursor: 'pointer',
    fontSize: 16,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  toolbar: {
    display: 'flex',
    gap: 8,
    padding: '12px 20px',
    borderBottom: '1px solid #f0f0f0',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  select: {
    padding: '6px 10px',
    borderRadius: 6,
    border: '1px solid #ddd',
    fontSize: 13,
    outline: 'none',
  },
  searchInput: {
    padding: '6px 12px',
    borderRadius: 6,
    border: '1px solid #ddd',
    fontSize: 13,
    outline: 'none',
    width: 180,
  },
  primaryBtn: {
    padding: '6px 16px',
    borderRadius: 6,
    border: 'none',
    background: '#1976D2',
    color: '#fff',
    fontSize: 13,
    cursor: 'pointer',
    fontWeight: 500,
  },
  secondaryBtn: {
    padding: '6px 16px',
    borderRadius: 6,
    border: '1px solid #ddd',
    background: '#fff',
    color: '#333',
    fontSize: 13,
    cursor: 'pointer',
  },
  list: {
    flex: 1,
    overflow: 'auto',
    padding: '0 20px',
  },
  empty: {
    textAlign: 'center',
    padding: '60px 20px',
    color: '#999',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
  },
  th: {
    textAlign: 'left',
    padding: '10px 8px',
    borderBottom: '2px solid #e8e8e8',
    fontSize: 13,
    color: '#666',
    fontWeight: 600,
    position: 'sticky' as any,
    top: 0,
    background: '#fff',
  },
  tr: {
    borderBottom: '1px solid #f0f0f0',
  },
  td: {
    padding: '10px 8px',
    fontSize: 13,
    color: '#333',
    verticalAlign: 'middle',
  },
  tag: {
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: 4,
    background: '#e3f2fd',
    color: '#1976D2',
    fontSize: 12,
  },
  toggleBtn: {
    padding: '3px 10px',
    borderRadius: 4,
    border: 'none',
    color: '#fff',
    fontSize: 12,
    cursor: 'pointer',
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
    padding: '10px 20px',
    borderTop: '1px solid #eee',
    fontSize: 12,
    color: '#999',
  },
  // 弹窗
  modalOverlay: {
    position: 'fixed',
    inset: 0,
    zIndex: 1100,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'rgba(0,0,0,0.3)',
  },
  modal: {
    width: '90%',
    maxWidth: 560,
    background: '#fff',
    borderRadius: 12,
    padding: 24,
    boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
  },
  formGroup: {
    marginBottom: 12,
    flex: 1,
  },
  formRow: {
    display: 'flex',
    gap: 12,
  },
  label: {
    display: 'block',
    fontSize: 13,
    color: '#666',
    marginBottom: 4,
    fontWeight: 500,
  },
  textInput: {
    width: '100%',
    padding: '8px 12px',
    borderRadius: 6,
    border: '1px solid #ddd',
    fontSize: 14,
    outline: 'none',
    boxSizing: 'border-box' as any,
  },
  modalBtns: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: 8,
    marginTop: 16,
  },
};
