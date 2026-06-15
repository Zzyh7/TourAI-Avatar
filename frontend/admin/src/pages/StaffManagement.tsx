import { useState, useEffect } from 'react';

interface Staff { id: number; account: string; active: number; }

export default function StaffManagement() {
  const [list, setList] = useState<Staff[]>([]);
  const [account, setAccount] = useState('');
  const [password, setPassword] = useState('');
  const [editId, setEditId] = useState<number | null>(null);
  const [msg, setMsg] = useState('');

  const api = async (path: string, opts?: RequestInit) => {
    const r = await fetch(path, opts);
    const t = await r.text();
    try { return JSON.parse(t); } catch { return t; }
  };

  const load = async () => {
    const data = await api('/api/admin/staff');
    setList(Array.isArray(data) ? data : []);
  };
  useEffect(() => { load(); }, []);

  const save = async () => {
    if (!account || (!editId && !password)) return;
    if (editId) {
      await api(`/api/admin/staff/${editId}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account: account || undefined, password: password || undefined }),
      });
    } else {
      await api('/api/admin/staff', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account, password }),
      });
    }
    setAccount(''); setPassword(''); setEditId(null); setMsg('保存成功'); load();
  };

  const toggleActive = async (s: Staff) => {
    await api(`/api/admin/staff/${s.id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active: s.active ? 0 : 1 }),
    });
    load();
  };

  const remove = async (id: number) => {
    await api(`/api/admin/staff/${id}`, { method: 'DELETE' });
    setMsg('已删除'); load();
  };

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 16 }}>🔑 员工账号管理</h2>
      {msg && <p style={{ color: '#34d399', marginBottom: 8 }}>{msg}</p>}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        <input placeholder="账号" value={account} onChange={e => setAccount(e.target.value)}
          style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #e0e0e0', fontSize: 14 }} />
        <input placeholder={editId ? '新密码(留空不改)' : '密码'} value={password}
          onChange={e => setPassword(e.target.value)} type="password"
          style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #e0e0e0', fontSize: 14 }} />
        <button onClick={save} style={{ padding: '8px 20px', borderRadius: 8, border: 'none', background: '#c9a050', color: '#fff', cursor: 'pointer', fontWeight: 600 }}>
          {editId ? '更新' : '添加'}
        </button>
        {editId && <button onClick={() => { setEditId(null); setAccount(''); setPassword(''); }}
          style={{ padding: '8px 20px', borderRadius: 8, border: 'none', background: '#999', color: '#fff', cursor: 'pointer' }}>取消</button>}
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead><tr style={{ borderBottom: '1px solid #e0e0e0' }}>
          <th style={{ textAlign: 'left', padding: '10px 12px', fontSize: 13, color: '#666' }}>ID</th>
          <th style={{ textAlign: 'left', padding: '10px 12px', fontSize: 13, color: '#666' }}>账号</th>
          <th style={{ textAlign: 'left', padding: '10px 12px', fontSize: 13, color: '#666' }}>状态</th>
          <th style={{ textAlign: 'left', padding: '10px 12px', fontSize: 13, color: '#666' }}>操作</th>
        </tr></thead>
        <tbody>{list.map(s => (
          <tr key={s.id} style={{ borderBottom: '1px solid #f0f0f0' }}>
            <td style={{ padding: '10px 12px', fontSize: 14 }}>{s.id}</td>
            <td style={{ padding: '10px 12px', fontSize: 14 }}>{s.account}</td>
            <td style={{ padding: '10px 12px', fontSize: 14, color: s.active ? '#34d399' : '#f87171' }}>{s.active ? '启用' : '禁用'}</td>
            <td style={{ padding: '10px 12px', fontSize: 14 }}>
              <button onClick={() => { setEditId(s.id); setAccount(s.account); setPassword(''); }}
                style={btnSm('#c9a050')}>编辑</button>
              <button onClick={() => toggleActive(s)} style={btnSm(s.active ? '#f59e0b' : '#34d399')}>
                {s.active ? '禁用' : '启用'}</button>
              <button onClick={() => remove(s.id)} style={btnSm('#f87171')}>删除</button>
            </td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}
const btnSm = (bg: string) => ({ padding: '4px 12px', borderRadius: 6, border: 'none', color: '#fff', cursor: 'pointer', fontSize: 12, marginRight: 6, background: bg } as React.CSSProperties);
