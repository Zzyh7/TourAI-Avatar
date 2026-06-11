/**
 * 管理后台主应用 —— 页面路由
 */
import { useState } from 'react';
import Layout, { type PageKey } from './components/Layout';
import Dashboard from './pages/Dashboard';
import CommonDialogues from './pages/CommonDialogues';
import Sessions from './pages/Sessions';
import Documents from './pages/Documents';
import ScenicSpots from './pages/ScenicSpots';
import Config from './pages/Config';

export default function App() {
  const [page, setPage] = useState<PageKey>('dashboard');

  const renderPage = () => {
    switch (page) {
      case 'dashboard':
        return <Dashboard />;
      case 'dialogues':
        return <CommonDialogues />;
      case 'sessions':
        return <Sessions />;
      case 'documents':
        return <Documents />;
      case 'spots':
        return <ScenicSpots />;
      case 'config':
        return <Config />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <Layout active={page} onNavigate={setPage}>
      {renderPage()}
    </Layout>
  );
}
