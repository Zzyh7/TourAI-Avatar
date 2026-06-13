/**
 * 管理后台主应用 —— 页面路由
 */
import { useState } from 'react';
import Layout, { type PageKey } from './components/Layout';
import Dashboard from './pages/Dashboard';
import SpotPopularity from './pages/SpotPopularity';
import TimeComparison from './pages/TimeComparison';
import QAAnalysis from './pages/QAAnalysis';
import VisitorProfile from './pages/VisitorProfile';
import NegativeFeedback from './pages/NegativeFeedback';
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
      case 'spots-hot':
        return <SpotPopularity />;
      case 'time-compare':
        return <TimeComparison />;
      case 'qa-analysis':
        return <QAAnalysis />;
      case 'visitors':
        return <VisitorProfile />;
      case 'negative':
        return <NegativeFeedback />;
      case 'dialogues':
        return <CommonDialogues />;
      case 'sessions':
        return <Sessions />;
      case 'documents':
        return <Documents />;
      case 'scenic-spots':
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
