/**
 * 管理后台布局 —— 侧边栏 + 内容区
 */
import { type ReactNode } from 'react';

export type PageKey = 'dashboard' | 'spots-hot' | 'time-compare' | 'qa-analysis' | 'visitors' | 'negative' | 'dialogues' | 'sessions' | 'documents' | 'scenic-spots' | 'config';

interface Props {
  active: PageKey;
  onNavigate: (page: PageKey) => void;
  children: ReactNode;
}

const NAV_ITEMS: { key: PageKey; label: string; icon: string }[] = [
  { key: 'dashboard', label: '数据大屏', icon: '📊' },
  { key: 'spots-hot', label: '景点热度', icon: '🔥' },
  { key: 'time-compare', label: '时间对比', icon: '📅' },
  { key: 'qa-analysis', label: '问答分析', icon: '💬' },
  { key: 'visitors', label: '游客画像', icon: '🧑' },
  { key: 'negative', label: '负面反馈', icon: '⚠️' },
  { key: 'dialogues', label: '常用对话', icon: '📝' },
  { key: 'sessions', label: '会话记录', icon: '📋' },
  { key: 'documents', label: '知识库', icon: '📚' },
  { key: 'scenic-spots', label: '景点管理', icon: '🏛️' },
  { key: 'config', label: '系统配置', icon: '⚙️' },
];

export default function Layout({ active, onNavigate, children }: Props) {
  return (
    <div style={styles.wrapper}>
      {/* 侧边栏 */}
      <aside style={styles.sidebar}>
        <div style={styles.logo}>
          <span style={styles.logoIcon}>🏔️</span>
          <span style={styles.logoText}>景区导览后台</span>
        </div>
        <nav style={styles.nav}>
          {NAV_ITEMS.map(item => (
            <button
              key={item.key}
              onClick={() => onNavigate(item.key)}
              style={{
                ...styles.navItem,
                ...(active === item.key ? styles.navItemActive : {}),
              }}
            >
              <span style={styles.navIcon}>{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
        <div style={styles.sidebarFooter}>
          <span style={{ fontSize: 12, color: '#999' }}>v2.0.0</span>
        </div>
      </aside>

      {/* 内容区 */}
      <main style={styles.main}>
        {children}
      </main>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    display: 'flex',
    height: '100vh',
    overflow: 'hidden',
  },
  sidebar: {
    width: 220,
    background: '#1a1a2e',
    color: '#fff',
    display: 'flex',
    flexDirection: 'column',
    flexShrink: 0,
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '20px 18px',
    borderBottom: '1px solid rgba(255,255,255,0.08)',
  },
  logoIcon: {
    fontSize: 24,
  },
  logoText: {
    fontSize: 16,
    fontWeight: 600,
    letterSpacing: 0.5,
  },
  nav: {
    flex: 1,
    padding: '12px 10px',
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
    overflow: 'auto',
  },
  navItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '10px 14px',
    borderRadius: 8,
    border: 'none',
    background: 'transparent',
    color: 'rgba(255,255,255,0.65)',
    fontSize: 14,
    cursor: 'pointer',
    textAlign: 'left' as const,
    transition: 'all 0.15s',
  },
  navItemActive: {
    background: 'rgba(255,255,255,0.12)',
    color: '#fff',
    fontWeight: 500,
  },
  navIcon: {
    fontSize: 18,
    width: 24,
    textAlign: 'center' as const,
  },
  sidebarFooter: {
    padding: '12px 18px',
    borderTop: '1px solid rgba(255,255,255,0.08)',
  },
  main: {
    flex: 1,
    overflow: 'auto',
    padding: 24,
  },
};
