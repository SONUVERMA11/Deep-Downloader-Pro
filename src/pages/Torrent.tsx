import { useState } from 'react';
import { useAppStore } from '../store/useAppStore';
import { Magnet, Search, Plus } from 'lucide-react';
import { api } from '../lib/api';

export function Torrent() {
  const { torrents } = useAppStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [magnetInput, setMagnetInput] = useState('');

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    try {
      const result = await api.searchTorrents(searchQuery);
      console.log('Search results:', result);
    } catch (err) {
      console.error('Torrent search failed:', err);
    }
  };

  const handleAddMagnet = async () => {
    if (!magnetInput.trim()) return;
    try {
      await api.addTorrent(magnetInput);
      setMagnetInput('');
    } catch (err) {
      console.error('Add torrent failed:', err);
    }
  };

  return (
    <div className="animate-in">
      <div className="page-header">
        <h1 className="page-title">Torrent Client</h1>
        <p className="page-subtitle">Search, download, and manage torrents</p>
      </div>

      {/* Search */}
      <div className="url-input-container" style={{ marginBottom: 16 }}>
        <div style={{ padding: '0 8px', color: 'var(--text-tertiary)', display: 'flex', alignItems: 'center' }}>
          <Search size={18} />
        </div>
        <input
          className="input"
          placeholder="Search torrents across TPB, 1337x, YTS, Nyaa..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
        />
        <button className="btn btn-primary" onClick={handleSearch} style={{ minWidth: 100 }}>
          <Search size={14} /> Search
        </button>
      </div>

      {/* Add Magnet */}
      <div className="url-input-container" style={{ marginBottom: 24 }}>
        <div style={{ padding: '0 8px', color: 'var(--text-tertiary)', display: 'flex', alignItems: 'center' }}>
          <Magnet size={18} />
        </div>
        <input
          className="input"
          placeholder="Paste magnet link or drag .torrent file here..."
          value={magnetInput}
          onChange={(e) => setMagnetInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAddMagnet()}
        />
        <button className="btn btn-secondary" onClick={handleAddMagnet} style={{ minWidth: 100 }}>
          <Plus size={14} /> Add
        </button>
      </div>

      {/* Torrent List */}
      {torrents.length > 0 ? (
        <div className="download-list">
          {torrents.map((t) => (
            <div key={t.info_hash} className="card" style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <Magnet size={20} style={{ color: 'var(--accent)', flexShrink: 0 }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 600, fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.name}</div>
                <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2 }}>
                  Seeds: {t.seeds} • Peers: {t.peers} • {(t.progress * 100).toFixed(1)}%
                </div>
                <div className="progress-bar" style={{ marginTop: 6 }}>
                  <div className="progress-bar-fill animated" style={{ width: `${t.progress * 100}%` }} />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <Magnet className="empty-state-icon" size={64} />
          <div className="empty-state-title">No active torrents</div>
          <div className="empty-state-text">Search for torrents or paste a magnet link to start downloading. Supports DHT, PEX, and sequential download for streaming.</div>
        </div>
      )}
    </div>
  );
}
