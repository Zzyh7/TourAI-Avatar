/**
 * 会话&对话记录管理页 —— 查看会话列表、对话详情、删除
 */
import { useState, useEffect, useCallback } from 'react';
import {
  getSessions,
  getSessionCount,
  getSessionDetail,
  deleteSession,
  deleteConversation,
  type SessionItem,
  type SessionDetail,
  type ConversationItem,
} from '../services/api';

export default function Sessions() {
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [tagFilter, setTagFilter] = useState('');
  const [loading, setLoading] = useState(false);

  // 详情弹窗
  const [detailId, setDetailId] = useState<string | null>(null);
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // 删除确认
  const [deleteTarget, setDeleteTarget] = useState<{ type: 'session' | 'conv'; id: string | number } | null>(null);

  const PAGE_SIZE = 20;

  const loadSessions = useCallback(async () => {
    setLoading(true);
    try {
      const [data, count] = await Promise.all([
        getSessions({ search: search || undefined, tag: tagFilter || undefined, page, page_size: PAGE_SIZE }),
        getSessionCount(),
      ]);
      setSessions(data);
      setTotal(count);
    } catch (e) {
      console.error('加载会话失败:', e);
    } finally {
      setLoading(false);
    }
  }, [search, tagFilter, page]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const openDetail = async (sessionId: string) => {
    setDetailId(sessionId);
    setDetailLoading(true);
    try {
      const data = await getSessionDetail(sessionId);
      setDetail(data);
    } catch (e) {
      console.error('加载会话详情失败:', e);
    } finally {
      setDetailLoading(false);
    }
  };

  const closeDetail = () => {
    setDetailId(null);
    setDetail(null);
  };

  const handleDeleteSession = async (id: string) => {
    try {
      await deleteSession(id);
      setDeleteTarget(null);
      if (detailId === id) closeDetail();
      loadSessions();
    } catch (e) {
      console.error('删除会话失败:', e);
    }
  };

  const handleDeleteConv = async (id: number) => {
    try {
      await deleteConversation(id);
      setDeleteTarget(null);
      if (detailId) openDetail(detailId); // 刷新详情
    } catch (e) {
      console.error('删除对话失败:', e);
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const tagLabel = (tag: string) => {
    const map: Record<string, string> = {
      '家庭游': '👨‍👩‍👧 家庭游',
      '情侣游': '💑 情侣游',
      '文化深度游': '🏛️ 文化深度游',
      '休闲游': '🌿 休闲游',
    };
    return map[tag] || tag || '未标记';
  };

  const sentimentColor = (s: string) => {
    if (s === '正面') return '#C9A24E';
    if (s === '负面') return '#c0392b';
    return '#D4943A';
  };

  return (
    <div>
      <h1 style={styles.title}>📝 会话记录</h1>
      <p style={styles.subtitle}>查看和管理所有对话会话及聊天记录</p>

      {/* 工具栏 */}
      <div style={styles.toolbar}>
        <input
          type="text"
          placeholder="搜索会话ID..."
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
          style={styles.searchInput}
        />
        <select
          value={tagFilter}
          onChange={e => { setTagFilter(e.target.value); setPage(1); }}
          style={styles.select}
        >
          <option value="">全部标签</option>
          <option value="家庭游">家庭游</option>
          <option value="情侣游">情侣游</option>
          <option value="文化深度游">文化深度游</option>
          <option value="休闲游">休闲游</option>
        </select>
        <div style={{ flex: 1 }} />
        <span style={{ fontSize: 13, color: '#8B7355' }}>共 {total} 个会话</span>
      </div>

      {/* 列表 */}
      <div style={styles.tableWrap}>
        {loading ? (
          <div style={styles.empty}>加载中...</div>
        ) : sessions.length === 0 ? (
          <div style={styles.empty}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>📭</div>
            <div>暂无会话记录</div>
          </div>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>会话 ID</th>
                <th style={styles.th}>游客标签</th>
                <th style={styles.th}>对话数</th>
                <th style={styles.th}>创建时间</th>
                <th style={styles.th}>操作</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map(s => (
                <tr key={s.id} style={styles.tr}>
                  <td style={{ ...styles.td, fontFamily: 'monospace', fontSize: 12 }}>
                    {s.id}
                  </td>
                  <td style={styles.td}>
                    <span style={styles.tag}>{tagLabel(s.visitor_tag)}</span>
                  </td>
                  <td style={styles.td}>{s.conversation_count}</td>
                  <td style={{ ...styles.td, fontSize: 12, color: '#8B7355' }}>
                    {new Date(s.created_at).toLocaleString('zh-CN')}
                  </td>
                  <td style={styles.td}>
                    <button onClick={() => openDetail(s.id)} style={styles.actionBtn} title="查看详情">📋</button>
                    <button onClick={() => setDeleteTarget({ type: 'session', id: s.id })} style={styles.actionBtn} title="删除">🗑️</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* 分页 */}
      {totalPages > 1 && (
        <div style={styles.pagination}>
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page <= 1}
            style={{ ...styles.pageBtn, opacity: page <= 1 ? 0.4 : 1 }}
          >
            上一页
          </button>
          <span style={{ fontSize: 13, color: '#8B7355' }}>第 {page} / {totalPages} 页</span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            style={{ ...styles.pageBtn, opacity: page >= totalPages ? 0.4 : 1 }}
          >
            下一页
          </button>
        </div>
      )}

      {/* ====== 会话详情弹窗 ====== */}
      {detailId && (
        <div style={styles.modalOverlay} onClick={closeDetail}>
          <div style={{ ...styles.modal, maxWidth: 800, maxHeight: '80vh' }} onClick={e => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h3 style={{ margin: 0, fontSize: 16 }}>会话详情</h3>
              <button onClick={closeDetail} style={styles.closeBtn}>✕</button>
            </div>
            {detailLoading ? (
              <div style={{ textAlign: 'center', padding: 40, color: '#8B7355' }}>加载中...</div>
            ) : detail ? (
              <>
                <div style={styles.detailMeta}>
                  <span>ID: <code>{detail.id}</code></span>
                  <span>标签: {tagLabel(detail.visitor_tag)}</span>
                  <span>对话数: {detail.conversation_count}</span>
                  <span>创建: {new Date(detail.created_at).toLocaleString('zh-CN')}</span>
                </div>
                <div style={{ maxHeight: 400, overflow: 'auto' }}>
                  {detail.conversations.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: 30, color: '#E0D3C0' }}>暂无对话记录</div>
                  ) : (
                    detail.conversations.map(c => (
                      <div key={c.id} style={{
                        ...styles.convItem,
                        background: c.role === 'user' ? '#FFF5E0' : '#FFF9ED',
                        borderLeftColor: c.role === 'user' ? '#B8860B' : '#C9A24E',
                      }}>
                        <div style={styles.convMeta}>
                          <span style={{
                            ...styles.convRole,
                            color: c.role === 'user' ? '#B8860B' : '#C9A24E',
                          }}>
                            {c.role === 'user' ? '👤 用户' : '🤖 助手'}
                          </span>
                          {c.sentiment && (
                            <span style={{ ...styles.sentimentBadge, color: sentimentColor(c.sentiment) }}>
                              {c.sentiment}
                            </span>
                          )}
                          <span style={{ fontSize: 11, color: '#8B7355' }}>
                            {new Date(c.created_at).toLocaleString('zh-CN')}
                          </span>
                          {c.latency_ms > 0 && (
                            <span style={{ fontSize: 11, color: '#8B7355' }}>⏱ {c.latency_ms}ms</span>
                          )}
                          <div style={{ flex: 1 }} />
                          <button
                            onClick={() => setDeleteTarget({ type: 'conv', id: c.id })}
                            style={{ ...styles.actionBtn, fontSize: 12 }}
                            title="删除此条"
                          >
                            🗑️
                          </button>
                        </div>
                        <div style={styles.convContent}>{c.content}</div>
                      </div>
                    ))
                  )}
                </div>
              </>
            ) : (
              <div style={{ textAlign: 'center', padding: 40, color: '#8B7355' }}>加载失败</div>
            )}
          </div>
        </div>
      )}

      {/* ====== 删除确认 ====== */}
      {deleteTarget && (
        <div style={styles.modalOverlay} onClick={() => setDeleteTarget(null)}>
          <div style={{ ...styles.modal, maxWidth: 380 }} onClick={e => e.stopPropagation()}>
            <h3 style={{ margin: '0 0 12px', fontSize: 18 }}>确认删除</h3>
            <p style={{ fontSize: 14, color: '#8B7355', lineHeight: 1.6 }}>
              {deleteTarget.type === 'session'
                ? '确定要删除此会话及其所有对话记录吗？此操作不可恢复。'
                : '确定要删除此条对话记录吗？此操作不可恢复。'}
            </p>
            <div style={styles.modalBtns}>
              <button onClick={() => setDeleteTarget(null)} style={styles.secondaryBtn}>取消</button>
              <button
                onClick={() => {
                  if (deleteTarget.type === 'session') handleDeleteSession(deleteTarget.id as string);
                  else handleDeleteConv(deleteTarget.id as number);
                }}
                style={{ ...styles.primaryBtn, background: '#c0392b' }}
              >
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
    background: '#FFFDF5',
    padding: '12px 16px',
    borderRadius: 10,
    boxShadow: '0 1px 8px rgba(74,48,40,0.06)',
  },
  select: {
    padding: '7px 12px',
    borderRadius: 6,
    border: '1px solid #E0D3C0',
    fontSize: 13,
    outline: 'none',
    background: '#FFF9ED',
  },
  searchInput: {
    padding: '7px 14px',
    borderRadius: 6,
    border: '1px solid #E0D3C0',
    fontSize: 13,
    outline: 'none',
    width: 220,
  },
  primaryBtn: {
    padding: '7px 18px',
    borderRadius: 6,
    border: 'none',
    background: 'linear-gradient(135deg, #C9A24E, #8B6914)',
    color: '#fff',
    fontSize: 13,
    cursor: 'pointer',
    fontWeight: 500,
  },
  secondaryBtn: {
    padding: '7px 18px',
    borderRadius: 6,
    border: '1px solid #E0D3C0',
    background: '#FFF9ED',
    color: '#4A3028',
    fontSize: 13,
    cursor: 'pointer',
  },
  tableWrap: {
    background: '#FFFDF5',
    borderRadius: 10,
    boxShadow: '0 1px 8px rgba(74,48,40,0.06)',
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
    color: '#4A3028',
    fontWeight: 600,
    background: '#FFF9ED',
  },
  tr: {
    borderBottom: '1px solid #E0D3C0',
  },
  td: {
    padding: '10px 14px',
    fontSize: 13,
    color: '#4A3028',
    verticalAlign: 'middle' as const,
  },
  tag: {
    display: 'inline-block',
    padding: '2px 10px',
    borderRadius: 4,
    background: '#FFF5E0',
    color: '#8B6914',
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
  pagination: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 16,
    marginTop: 16,
  },
  pageBtn: {
    padding: '6px 16px',
    borderRadius: 6,
    border: '1px solid #E0D3C0',
    background: '#FFF9ED',
    fontSize: 13,
    cursor: 'pointer',
    color: '#4A3028',
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
    maxWidth: 800,
    maxHeight: '85vh',
    overflow: 'auto',
    background: '#FFFDF5',
    borderRadius: 12,
    padding: 24,
    boxShadow: '0 12px 48px rgba(74,48,40,0.18)',
  },
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
    paddingBottom: 12,
    borderBottom: '1px solid #E0D3C0',
  },
  closeBtn: {
    width: 32,
    height: 32,
    borderRadius: '50%',
    border: 'none',
    background: '#E0D3C0',
    cursor: 'pointer',
    fontSize: 16,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#4A3028',
  },
  detailMeta: {
    display: 'flex',
    gap: 16,
    flexWrap: 'wrap' as const,
    marginBottom: 16,
    fontSize: 13,
    color: '#8B7355',
  },
  convItem: {
    padding: '12px 14px',
    borderRadius: 8,
    marginBottom: 10,
    borderLeft: '3px solid #B8860B',
  },
  convMeta: {
    display: 'flex',
    gap: 10,
    alignItems: 'center',
    marginBottom: 6,
  },
  convRole: {
    fontSize: 12,
    fontWeight: 600,
  },
  sentimentBadge: {
    fontSize: 11,
    fontWeight: 500,
    padding: '1px 6px',
    borderRadius: 3,
    background: '#FFF9ED',
  },
  convContent: {
    fontSize: 14,
    color: '#4A3028',
    lineHeight: 1.7,
    whiteSpace: 'pre-wrap' as const,
  },
  modalBtns: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: 10,
    marginTop: 20,
  },
};
