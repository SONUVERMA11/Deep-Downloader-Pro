import { useAppStore, type PageId } from '../store/useAppStore';
import {
  Download, ListVideo, Magnet, MessageCircle, History, Settings,
  ChevronLeft, ChevronRight, Zap
} from 'lucide-react';

const navItems: { id: PageId; label: string; icon: React.ComponentType<any> }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: Download },
  { id: 'playlist', label: 'Playlists', icon: ListVideo },
  { id: 'torrent', label: 'Torrents', icon: Magnet },
  { id: 'telegram', label: 'Telegram', icon: MessageCircle },
  { id: 'history', label: 'History', icon: History },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export function Sidebar() {
  const { currentPage, setCurrentPage, sidebarExpanded, toggleSidebar } = useAppStore();

  return (
    <aside className={`sidebar ${sidebarExpanded ? 'expanded' : ''}`}>
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <Zap size={18} />
        </div>
        <span className="sidebar-title">DEEP DOWNLOADR</span>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <div
            key={item.id}
            className={`sidebar-item ${currentPage === item.id ? 'active' : ''}`}
            onClick={() => setCurrentPage(item.id)}
            role="button"
            tabIndex={0}
          >
            <item.icon className="sidebar-item-icon" size={20} />
            <span className="sidebar-item-label">{item.label}</span>
          </div>
        ))}
      </nav>

      <div className="sidebar-toggle" onClick={toggleSidebar} role="button" tabIndex={0}>
        {sidebarExpanded ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}
      </div>
    </aside>
  );
}
