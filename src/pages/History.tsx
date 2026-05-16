import { useAppStore } from '../store/useAppStore';
import { DownloadCard } from '../components/DownloadCard';
import { History as HistoryIcon, Trash2, Search } from 'lucide-react';
import { useState } from 'react';

export function History() {
  const { history } = useAppStore();
  const [filter, setFilter] = useState('');

  const filtered = history.filter((d) =>
    !filter || d.title.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="animate-in">
      <div className="page-header">
        <h1 className="page-title">History</h1>
        <p className="page-subtitle">All completed and past downloads</p>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        <div className="url-input-container" style={{ flex: 1 }}>
          <div style={{ padding: '0 8px', color: 'var(--text-tertiary)', display: 'flex', alignItems: 'center' }}>
            <Search size={16} />
          </div>
          <input className="input" placeholder="Search history..." value={filter} onChange={(e) => setFilter(e.target.value)} />
        </div>
        <button className="btn btn-secondary"><Trash2 size={14} /> Clear</button>
      </div>

      {filtered.length > 0 ? (
        <div className="download-list">
          {filtered.map((item) => (
            <DownloadCard key={item.download_id} item={item} />
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <HistoryIcon className="empty-state-icon" size={64} />
          <div className="empty-state-title">No download history</div>
          <div className="empty-state-text">Completed downloads will appear here. You can search, filter, and re-download from history.</div>
        </div>
      )}
    </div>
  );
}
