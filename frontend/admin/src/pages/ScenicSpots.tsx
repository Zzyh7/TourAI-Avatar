/**
 * 景点管理页 —— 增删改查
 */
import { useState, useEffect, useCallback } from 'react';
import {
  getScenicSpots,
  getScenicSpotCategories,
  createScenicSpot,
  updateScenicSpot,
  deleteScenicSpot,
  type ScenicSpot,
} from '../services/api';

const DEFAULT_FORM: Partial<ScenicSpot> = {
  name: '',
  latitude: 0,
  longitude: 0,
  trigger_radius: 100,
  description: '',
  audio_intro_path: '',
  category: '',
  visit_duration: 60,
};

export default function ScenicSpots() {
  const [spots, setSpots] = useState<ScenicSpot[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [filterCategory, setFilterCategory] = useState('');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);

  // 编辑弹窗
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<Partial<ScenicSpot>>({ ...DEFAULT_FORM });

  // 删除确认
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [list, cats] = await Promise.all([
        getScenicSpots({ category: filterCategory || undefined, search: search || undefined }),
        getScenicSpotCategories(),
      ]);
      setSpots(list);
      setCategories(cats);
    } catch (e) {
      console.error('加载景点失败:', e);
    } finally {
      setLoading(false);
    }
  }, [filterCategory, search]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const openCreate = () => {
    setEditingId(null);
    setForm({ ...DEFAULT_FORM });
    setShowForm(true);
  };

  const openEdit = (spot: ScenicSpot) => {
    setEditingId(spot.id);
    setForm({
      name: spot.name,
      latitude: spot.latitude,
      longitude: spot.longitude,
      trigger_radius: spot.trigger_radius,
      description: spot.description,
      audio_intro_path: spot.audio_intro_path,
      category: spot.category,
      visit_duration: spot.visit_duration,
    });
    setShowForm(true);
  };

  const handleSubmit = async () => {
    if (!form.name?.trim()) return;
    try {
      if (editingId) {
        await updateScenicSpot(editingId, form);
      } else {
        await createScenicSpot(form);
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
      await deleteScenicSpot(id);
      setDeleteId(null);
      loadData();
    } catch (e) {
      console.error('删除失败:', e);
    }
  };

  return (
    <div>
      <h1 style={styles.title}>📍 景点管理</h1>
      <p style={styles.subtitle}>管理景区预设景点信息，用于 GPS 附近景点推荐</p>

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
        <input
          type="text"
          placeholder="搜索景点名称..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={styles.searchInput}
        />
        <div style={{ flex: 1 }} />
        <button onClick={openCreate} style={styles.primaryBtn}>＋ 新增景点</button>
      </div>

      {/* 列表 */}
      <div style={styles.tableWrap}>
        {loading ? (
          <div style={styles.empty}>加载中...</div>
        ) : spots.length === 0 ? (
          <div style={styles.empty}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>📍</div>
            <div>暂无景点数据</div>
          </div>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>名称</th>
                <th style={styles.th}>坐标</th>
                <th style={styles.th}>触发半径</th>
                <th style={styles.th}>分类</th>
                <th style={styles.th}>游览时长</th>
                <th style={styles.th}>创建时间</th>
                <th style={styles.th}>操作</th>
              </tr>
            </thead>
            <tbody>
              {spots.map(s => (
                <tr key={s.id} style={styles.tr}>
                  <td style={{ ...styles.td, fontWeight: 500 }}>{s.name}</td>
                  <td style={{ ...styles.td, fontFamily: 'monospace', fontSize: 12 }}>
                    {s.latitude.toFixed(4)}, {s.longitude.toFixed(4)}
                  </td>
                  <td style={styles.td}>{s.trigger_radius}m</td>
                  <td style={styles.td}>
                    {s.category ? <span style={styles.tag}>{s.category}</span> : '-'}
                  </td>
                  <td style={styles.td}>{s.visit_duration} 分钟</td>
                  <td style={{ ...styles.td, fontSize: 12, color: '#999' }}>
                    {s.created_at ? new Date(s.created_at).toLocaleString('zh-CN') : '-'}
                  </td>
                  <td style={styles.td}>
                    <button onClick={() => openEdit(s)} style={styles.actionBtn} title="编辑">✏️</button>
                    <button onClick={() => setDeleteId(s.id)} style={styles.actionBtn} title="删除">🗑️</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ====== 新增/编辑弹窗 ====== */}
      {showForm && (
        <div style={styles.modalOverlay} onClick={() => setShowForm(false)}>
          <div style={styles.modal} onClick={e => e.stopPropagation()}>
            <h3 style={{ margin: '0 0 20px', fontSize: 18 }}>{editingId ? '编辑景点' : '新增景点'}</h3>
            <div style={styles.formGroup}>
              <label style={styles.label}>景点名称 *</label>
              <input
                style={styles.textInput}
                value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value })}
                placeholder="景点名称"
              />
            </div>
            <div style={styles.formRow}>
              <div style={styles.formGroup}>
                <label style={styles.label}>纬度</label>
                <input
                  type="number"
                  step="0.0001"
                  style={styles.textInput}
                  value={form.latitude}
                  onChange={e => setForm({ ...form, latitude: Number(e.target.value) })}
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>经度</label>
                <input
                  type="number"
                  step="0.0001"
                  style={styles.textInput}
                  value={form.longitude}
                  onChange={e => setForm({ ...form, longitude: Number(e.target.value) })}
                />
              </div>
            </div>
            <div style={styles.formRow}>
              <div style={styles.formGroup}>
                <label style={styles.label}>触发半径（米）</label>
                <input
                  type="number"
                  style={styles.textInput}
                  value={form.trigger_radius}
                  onChange={e => setForm({ ...form, trigger_radius: Number(e.target.value) })}
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>建议游览时长（分钟）</label>
                <input
                  type="number"
                  style={styles.textInput}
                  value={form.visit_duration}
                  onChange={e => setForm({ ...form, visit_duration: Number(e.target.value) })}
                />
              </div>
            </div>
            <div style={styles.formGroup}>
              <label style={styles.label}>分类</label>
              <input
                style={styles.textInput}
                value={form.category}
                onChange={e => setForm({ ...form, category: e.target.value })}
                placeholder="如：古建筑、自然景观、博物馆"
              />
            </div>
            <div style={styles.formGroup}>
              <label style={styles.label}>景点描述</label>
              <textarea
                style={{ ...styles.textInput, minHeight: 80, resize: 'vertical' }}
                value={form.description}
                onChange={e => setForm({ ...form, description: e.target.value })}
                placeholder="景点详细介绍..."
              />
            </div>
            <div style={styles.formGroup}>
              <label style={styles.label}>讲解音频路径（可选）</label>
              <input
                style={styles.textInput}
                value={form.audio_intro_path}
                onChange={e => setForm({ ...form, audio_intro_path: e.target.value })}
                placeholder="预生成讲解音频的文件路径"
              />
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

      {/* ====== 删除确认 ====== */}
      {deleteId !== null && (
        <div style={styles.modalOverlay} onClick={() => setDeleteId(null)}>
          <div style={{ ...styles.modal, maxWidth: 380 }} onClick={e => e.stopPropagation()}>
            <h3 style={{ margin: '0 0 12px', fontSize: 18 }}>确认删除</h3>
            <p style={{ fontSize: 14, color: '#666', lineHeight: 1.6 }}>确定要删除此景点吗？此操作不可恢复。</p>
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

const styles: Record<string, React.CSSProperties> = {
  title: {
    fontSize: 22,
    fontWeight: 600,
    marginBottom: 4,
    color: '#1a1a2e',
  },
  subtitle: {
    fontSize: 13,
    color: '#999',
    marginBottom: 20,
  },
  toolbar: {
    display: 'flex',
    gap: 10,
    marginBottom: 16,
    alignItems: 'center',
    background: '#fff',
    padding: '12px 16px',
    borderRadius: 10,
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
  },
  select: {
    padding: '7px 12px',
    borderRadius: 6,
    border: '1px solid #ddd',
    fontSize: 13,
    outline: 'none',
    background: '#fff',
  },
  searchInput: {
    padding: '7px 14px',
    borderRadius: 6,
    border: '1px solid #ddd',
    fontSize: 13,
    outline: 'none',
    width: 200,
  },
  primaryBtn: {
    padding: '7px 18px',
    borderRadius: 6,
    border: 'none',
    background: '#1976D2',
    color: '#fff',
    fontSize: 13,
    cursor: 'pointer',
    fontWeight: 500,
  },
  secondaryBtn: {
    padding: '7px 18px',
    borderRadius: 6,
    border: '1px solid #ddd',
    background: '#fff',
    color: '#333',
    fontSize: 13,
    cursor: 'pointer',
  },
  tableWrap: {
    background: '#fff',
    borderRadius: 10,
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
    overflow: 'auto',
  },
  empty: {
    textAlign: 'center',
    padding: 60,
    color: '#999',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
  },
  th: {
    textAlign: 'left' as const,
    padding: '12px 14px',
    borderBottom: '2px solid #e8e8e8',
    fontSize: 13,
    color: '#666',
    fontWeight: 600,
    background: '#fafafa',
  },
  tr: {
    borderBottom: '1px solid #f0f0f0',
  },
  td: {
    padding: '10px 14px',
    fontSize: 13,
    color: '#333',
    verticalAlign: 'middle' as const,
  },
  tag: {
    display: 'inline-block',
    padding: '2px 10px',
    borderRadius: 4,
    background: '#fff3e0',
    color: '#E65100',
    fontSize: 12,
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
  // 弹窗
  modalOverlay: {
    position: 'fixed' as const,
    inset: 0,
    zIndex: 1100,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'rgba(0,0,0,0.35)',
  },
  modal: {
    width: '90%',
    maxWidth: 560,
    background: '#fff',
    borderRadius: 12,
    padding: 28,
    boxShadow: '0 12px 48px rgba(0,0,0,0.18)',
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
    border: '1px solid #ddd',
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
