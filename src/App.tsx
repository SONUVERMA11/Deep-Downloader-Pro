import { useEffect } from 'react';
import { useAppStore } from './store/useAppStore';
import { Sidebar } from './components/Sidebar';
import { StatusBar } from './components/StatusBar';
import { Dashboard } from './pages/Dashboard';
import { Playlist } from './pages/Playlist';
import { Torrent } from './pages/Torrent';
import { Telegram } from './pages/Telegram';
import { History } from './pages/History';
import { Settings } from './pages/Settings';
import { api, wsClient } from './lib/api';

const pages: Record<string, React.ComponentType> = {
  dashboard: Dashboard,
  playlist: Playlist,
  torrent: Torrent,
  telegram: Telegram,
  history: History,
  settings: Settings,
};

export default function App() {
  const { currentPage, sidebarExpanded, theme, setBackendConnected, setStats, setDownloads, setHistory, updateDownload } = useAppStore();

  // Apply theme on mount
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  // Connect to backend on mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        await api.health();
        setBackendConnected(true);
        // Load initial data
        const [downloads, history, stats] = await Promise.all([
          api.getDownloads().catch(() => ({ downloads: [] })),
          api.getHistory().catch(() => ({ history: [] })),
          api.getStats().catch(() => ({})),
        ]);
        setDownloads(downloads.downloads || []);
        setHistory(history.history || []);
        setStats(stats);
      } catch {
        setBackendConnected(false);
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  // WebSocket for real-time progress
  useEffect(() => {
    wsClient.connect();
    const unsub1 = wsClient.on('connected', () => setBackendConnected(true));
    const unsub2 = wsClient.on('disconnected', () => setBackendConnected(false));
    const unsub3 = wsClient.on('progress', (data: any) => {
      updateDownload(data.download_id, {
        progress: data.progress,
        speed: data.speed,
        eta: data.eta,
        status: data.status,
      });
    });
    return () => { unsub1(); unsub2(); unsub3(); wsClient.disconnect(); };
  }, []);

  const PageComponent = pages[currentPage] || Dashboard;

  return (
    <div className="app-layout">
      <Sidebar />
      <main className={`main-content ${sidebarExpanded ? 'sidebar-expanded' : ''}`}>
        <div className="page-container">
          <PageComponent />
        </div>
      </main>
      <StatusBar />
    </div>
  );
}
