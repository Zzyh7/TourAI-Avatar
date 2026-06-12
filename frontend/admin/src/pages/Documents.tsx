/**
 * 知识库文档管理页 —— 上传/查看/删除
 */
import { useState, useEffect, useRef } from 'react';
import {
  getDocuments,
  uploadDocument,
  deleteDocument,
  type DocumentItem,
} from '../services/api';

const TYPE_LABELS: Record<string, string> = {
  pdf: '📄 PDF',
  docx: '📝 Word',
  doc: '📝 Word',
  txt: '📃 文本',
};

export default function Documents() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState('');
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const loadDocs = async () => {
    setLoading(true);
    try {
      const data = await getDocuments();
      setDocuments(data);
    } catch (e) {
      console.error('加载文档列表失败:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocs();
  }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadMsg('');
    try {
      const result = await uploadDocument(file);
      if (result.error) {
        setUploadMsg(`❌ ${result.error}`);
      } else {
        setUploadMsg(`✅ ${result.message || '上传成功'}`);
        loadDocs();
      }
    } catch (err: any) {
      setUploadMsg(`❌ 上传失败: ${err.message}`);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteDocument(id);
      setDeleteId(null);
      loadDocs();
    } catch (e) {
      console.error('删除失败:', e);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div>
      <h1 style={styles.title}>📚 知识库</h1>
      <p style={styles.subtitle}>管理景区知识库文档，支持 PDF / Word / TXT 上传，自动分块和向量化</p>

      {/* 工具栏 */}
      <div style={styles.toolbar}>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.docx,.doc,.txt"
          onChange={handleUpload}
          style={{ display: 'none' }}
        />
        <button
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          style={styles.primaryBtn}
        >
          {uploading ? '上传中...' : '📤 上传文档'}
        </button>
        {uploadMsg && (
          <span style={{
            fontSize: 13,
            color: uploadMsg.startsWith('✅') ? '#4CAF50' : '#f44336',
          }}>
            {uploadMsg}
          </span>
        )}
        <div style={{ flex: 1 }} />
        <span style={{ fontSize: 13, color: '#999' }}>共 {documents.length} 个文档</span>
      </div>

      {/* 列表 */}
      <div style={styles.tableWrap}>
        {loading ? (
          <div style={styles.empty}>加载中...</div>
        ) : documents.length === 0 ? (
          <div style={styles.empty}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>📭</div>
            <div>暂无文档</div>
            <div style={{ fontSize: 12, color: '#bbb', marginTop: 4 }}>点击「上传文档」添加知识库内容</div>
          </div>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>文件名</th>
                <th style={styles.th}>类型</th>
                <th style={styles.th}>分块数</th>
                <th style={styles.th}>大小</th>
                <th style={styles.th}>上传时间</th>
                <th style={styles.th}>操作</th>
              </tr>
            </thead>
            <tbody>
              {documents.map(d => (
                <tr key={d.id} style={styles.tr}>
                  <td style={styles.td}>{d.filename}</td>
                  <td style={styles.td}>
                    <span style={styles.typeTag}>{TYPE_LABELS[d.file_type] || d.file_type}</span>
                  </td>
                  <td style={styles.td}>{d.chunk_count} 块</td>
                  <td style={styles.td}>{formatSize(d.size_bytes)}</td>
                  <td style={{ ...styles.td, fontSize: 12, color: '#999' }}>
                    {d.uploaded_at ? new Date(d.uploaded_at).toLocaleString('zh-CN') : '-'}
                  </td>
                  <td style={styles.td}>
                    <button onClick={() => setDeleteId(d.id)} style={styles.actionBtn} title="删除">🗑️</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ====== 删除确认 ====== */}
      {deleteId !== null && (
        <div style={styles.modalOverlay} onClick={() => setDeleteId(null)}>
          <div style={{ ...styles.modal, maxWidth: 380 }} onClick={e => e.stopPropagation()}>
            <h3 style={{ margin: '0 0 12px', fontSize: 18 }}>确认删除</h3>
            <p style={{ fontSize: 14, color: '#666', lineHeight: 1.6 }}>
              确定要删除此文档吗？删除后相关的向量数据也将不可用。此操作不可恢复。
            </p>
            <div style={styles.modalBtns}>
              <button onClick={() => setDeleteId(null)} style={styles.secondaryBtn}>取消</button>
              <button
                onClick={() => handleDelete(deleteId)}
                style={{ ...styles.primaryBtn, background: '#ff4d4f' }}
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
    color: '#1a1a2e',
  },
  subtitle: {
    fontSize: 13,
    color: '#999',
    marginBottom: 20,
  },
  toolbar: {
    display: 'flex',
    gap: 12,
    marginBottom: 16,
    alignItems: 'center',
    background: '#fff',
    padding: '12px 16px',
    borderRadius: 10,
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
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
    padding: '12px 14px',
    fontSize: 13,
    color: '#333',
    verticalAlign: 'middle' as const,
  },
  typeTag: {
    display: 'inline-block',
    padding: '2px 10px',
    borderRadius: 4,
    background: '#e8f5e9',
    color: '#388E3C',
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
    maxWidth: 380,
    background: '#fff',
    borderRadius: 12,
    padding: 24,
    boxShadow: '0 12px 48px rgba(0,0,0,0.18)',
  },
  modalBtns: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: 10,
    marginTop: 20,
  },
};
