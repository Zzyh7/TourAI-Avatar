/**
 * 知识库文档管理页 —— 上传/查看/删除 + FAQ 导入（RAG API）
 */
import { useState, useEffect, useRef } from 'react';
import {
  getDocuments,
  uploadDocument,
  deleteDocument,
  getRAGHealth,
  importFAQ,
  type DocumentItem,
} from '../services/api';

const TYPE_LABELS: Record<string, string> = {
  pdf: '📄 PDF',
  docx: '📝 Word',
  doc: '📝 Word',
  txt: '📃 文本',
  md: '📝 Markdown',
};

export default function Documents() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState('');
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // FAQ 导入
  const [faqJson, setFaqJson] = useState('');
  const [importing, setImporting] = useState(false);
  const [importMsg, setImportMsg] = useState('');
  const [ragHealth, setRagHealth] = useState<{ faq_count: number; status: string } | null>(null);

  const loadDocs = async () => {
    setLoading(true);
    try {
      const [docs, health] = await Promise.all([
        getDocuments(),
        getRAGHealth().catch(() => null),
      ]);
      setDocuments(Array.isArray(docs) ? docs : []);
      setRagHealth(health);
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
        setUploadMsg(`✅ ${result.message || '上传成功，已自动分块和向量化'}`);
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

  const handleFaqImport = async () => {
    if (!faqJson.trim()) {
      setImportMsg('❌ 请粘贴 JSON 数据');
      return;
    }
    setImporting(true);
    setImportMsg('');
    try {
      const items = JSON.parse(faqJson);
      if (!Array.isArray(items)) {
        setImportMsg('❌ 请粘贴 JSON 数组格式');
        return;
      }
      const result = await importFAQ(items);
      setImportMsg(`✅ ${result.message || `成功导入 ${result.imported || items.length} 条`}`);
      setFaqJson('');
      loadDocs();
    } catch (err: any) {
      setImportMsg(`❌ 导入失败: ${err.message}`);
    } finally {
      setImporting(false);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div>
      <h1 style={s.title}>📚 知识库</h1>
      <p style={s.subtitle}>
        管理景区知识库文档（PDF/Word/TXT/Markdown），自动分块和向量化
        {ragHealth && (
          <span style={{ marginLeft: 12, color: '#1976d2', fontWeight: 500 }}>
            | RAG 状态: {ragHealth.status} | FAQ 条目: {ragHealth.faq_count}
          </span>
        )}
      </p>

      {/* 工具栏 */}
      <div style={s.toolbar}>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.docx,.doc,.txt,.md"
          onChange={handleUpload}
          style={{ display: 'none' }}
        />
        <button
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          style={s.primaryBtn}
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

      {/* 文档列表 */}
      <div style={s.tableWrap}>
        {loading ? (
          <div style={s.empty}>加载中...</div>
        ) : documents.length === 0 ? (
          <div style={s.empty}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>📭</div>
            <div>暂无文档</div>
            <div style={{ fontSize: 12, color: '#bbb', marginTop: 4 }}>点击「上传文档」添加知识库内容</div>
          </div>
        ) : (
          <table style={s.table}>
            <thead>
              <tr>
                <th style={s.th}>文件名</th>
                <th style={s.th}>类型</th>
                <th style={s.th}>分块数</th>
                <th style={s.th}>大小</th>
                <th style={s.th}>上传时间</th>
                <th style={s.th}>操作</th>
              </tr>
            </thead>
            <tbody>
              {documents.map(d => (
                <tr key={d.id} style={s.tr}>
                  <td style={s.td}>{d.filename}</td>
                  <td style={s.td}>
                    <span style={s.typeTag}>{TYPE_LABELS[d.file_type] || d.file_type}</span>
                  </td>
                  <td style={s.td}>{d.chunk_count} 块</td>
                  <td style={s.td}>{formatSize(d.size_bytes)}</td>
                  <td style={{ ...s.td, fontSize: 12, color: '#999' }}>
                    {d.uploaded_at ? new Date(d.uploaded_at).toLocaleString('zh-CN') : '-'}
                  </td>
                  <td style={s.td}>
                    <button onClick={() => setDeleteId(d.id)} style={s.actionBtn} title="删除">🗑️</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* FAQ 导入区 */}
      <div style={{ ...s.chartBox, marginTop: 20 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12, color: '#333' }}>📥 FAQ 批量导入</h3>
        <p style={{ fontSize: 13, color: '#999', marginBottom: 12 }}>
          粘贴 JSON 数组，每项包含 question 和 answer 字段
        </p>
        <textarea
          style={{
            width: '100%', minHeight: 120, padding: '12px 14px', borderRadius: 6,
            border: '1px solid #ddd', fontSize: 13, fontFamily: 'monospace',
            resize: 'vertical', boxSizing: 'border-box' as any,
          }}
          value={faqJson}
          onChange={e => setFaqJson(e.target.value)}
          placeholder={`[\n  { "question": "景区开放时间", "answer": "每日8:00-17:30" },\n  { "question": "门票多少钱", "answer": "成人票120元" }\n]`}
        />
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 12 }}>
          <button onClick={handleFaqImport} disabled={importing} style={s.primaryBtn}>
            {importing ? '导入中...' : '导入 FAQ'}
          </button>
          {importMsg && (
            <span style={{
              fontSize: 13,
              color: importMsg.startsWith('✅') ? '#4CAF50' : '#f44336',
            }}>
              {importMsg}
            </span>
          )}
        </div>
      </div>

      {/* 删除确认 */}
      {deleteId !== null && (
        <div style={s.modalOverlay} onClick={() => setDeleteId(null)}>
          <div style={{ ...s.modal, maxWidth: 380 }} onClick={e => e.stopPropagation()}>
            <h3 style={{ margin: '0 0 12px', fontSize: 18 }}>确认删除</h3>
            <p style={{ fontSize: 14, color: '#666', lineHeight: 1.6 }}>
              确定要删除此文档吗？删除后相关的向量数据也将不可用。此操作不可恢复。
            </p>
            <div style={s.modalBtns}>
              <button onClick={() => setDeleteId(null)} style={s.secondaryBtn}>取消</button>
              <button
                onClick={() => handleDelete(deleteId)}
                style={{ ...s.primaryBtn, background: '#ff4d4f' }}
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

const s: Record<string, React.CSSProperties> = {
  title: { fontSize: 22, fontWeight: 600, marginBottom: 4, color: '#1a1a2e' },
  subtitle: { fontSize: 13, color: '#999', marginBottom: 20 },
  toolbar: {
    display: 'flex', gap: 12, marginBottom: 16, alignItems: 'center',
    background: '#fff', padding: '12px 16px', borderRadius: 10,
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
  },
  primaryBtn: {
    padding: '7px 18px', borderRadius: 6, border: 'none',
    background: '#1976D2', color: '#fff', fontSize: 13, cursor: 'pointer', fontWeight: 500,
  },
  secondaryBtn: {
    padding: '7px 18px', borderRadius: 6, border: '1px solid #ddd',
    background: '#fff', color: '#333', fontSize: 13, cursor: 'pointer',
  },
  chartBox: {
    background: '#fff', borderRadius: 10, padding: 20,
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
  },
  tableWrap: {
    background: '#fff', borderRadius: 10,
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)', overflow: 'auto',
  },
  empty: { textAlign: 'center', padding: 60, color: '#999' },
  table: { width: '100%', borderCollapse: 'collapse' as const },
  th: {
    textAlign: 'left' as const, padding: '12px 14px',
    borderBottom: '2px solid #e8e8e8', fontSize: 13, color: '#666',
    fontWeight: 600, background: '#fafafa',
  },
  tr: { borderBottom: '1px solid #f0f0f0' },
  td: { padding: '12px 14px', fontSize: 13, color: '#333', verticalAlign: 'middle' as const },
  typeTag: {
    display: 'inline-block', padding: '2px 10px', borderRadius: 4,
    background: '#e8f5e9', color: '#388E3C', fontSize: 12, fontWeight: 500,
  },
  actionBtn: {
    padding: '4px 8px', borderRadius: 4, border: 'none',
    background: 'transparent', cursor: 'pointer', fontSize: 16,
  },
  modalOverlay: {
    position: 'fixed' as const, inset: 0, zIndex: 1100,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    background: 'rgba(0,0,0,0.35)',
  },
  modal: {
    width: '90%', maxWidth: 380, background: '#fff', borderRadius: 12,
    padding: 24, boxShadow: '0 12px 48px rgba(0,0,0,0.18)',
  },
  modalBtns: {
    display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 20,
  },
};
