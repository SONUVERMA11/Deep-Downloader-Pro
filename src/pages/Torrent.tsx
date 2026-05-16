import { useState } from 'react';
import { useAppStore } from '../store/useAppStore';
import { Magnet, Search, Plus, Download, ArrowUpDown, Users, HardDrive, Loader2, ChevronDown, ChevronRight } from 'lucide-react';
import { api } from '../lib/api';

interface SearchResult {
  title: string;
  seeds: number;
  leeches: number;
  size: string;
  magnet: string;
  source: string;
  category?: string;
  uploaded?: string;
}


export function Torrent() {
  const { torrents } = useAppStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [magnetInput, setMagnetInput] = useState('');
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [showResults, setShowResults] = useState(false);
  const [expandedTorrent, setExpandedTorrent] = useState<string | null>(null);
  const [addingMagnet, setAddingMagnet] = useState(false);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const result = await api.searchTorrents(searchQuery);
      setSearchResults(result.results || []);
      setShowResults(true);
    } catch (err) {
      console.error('Torrent search failed:', err);
    } finally {
      setSearching(false);
    }
  };

  const handleAddMagnet = async (magnet?: string) => {
    const uri = magnet || magnetInput.trim();
    if (!uri) return;
    setAddingMagnet(true);
    try {
      await api.addTorrent(uri);
      if (!magnet) setMagnetInput('');
      setShowResults(false);
    } catch (err) {
      console.error('Add torrent failed:', err);
    } finally {
      setAddingMagnet(false);
    }
  };

  const formatSpeed = (bps: number) => {
    if (bps < 1024) return `${bps} B/s`;
    if (bps < 1048576) return `${(bps / 1024).toFixed(1)} KB/s`;
    return `${(bps / 1048576).toFixed(1)} MB/s`;
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1073741824) return `${(bytes / 1048576).toFixed(1)} MB`;
    return `${(bytes / 1073741824).toFixed(2)} GB`;
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
          placeholder="Search torrents across TPB, YTS, Nyaa..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
        />
        <button className="btn btn-primary" onClick={handleSearch} disabled={searching} style={{ minWidth: 100 }}>
          {searching ? <><Loader2 size={14} className="spin" /> </> : <><Search size={14} /> Search</>}
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
        <button className="btn btn-secondary" onClick={() => handleAddMagnet()} disabled={addingMagnet} style={{ minWidth: 100 }}>
          {addingMagnet ? <Loader2 size={14} className="spin" /> : <><Plus size={14} /> Add</>}
        </button>
      </div>

      {/* Search Results */}
      {showResults && searchResults.length > 0 && (
        <div style={{ marginBottom: 28 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h2 style={{ fontSize: 15, fontWeight: 600 }}>
              Search Results ({searchResults.length})
            </h2>
            <button className="btn btn-ghost" style={{ fontSize: 12 }} onClick={() => setShowResults(false)}>
              Close
            </button>
          </div>
          <div className="download-list">
            {searchResults.map((result, i) => (
              <div key={i} className="card" style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '12px 14px' }}>
                <Magnet size={18} style={{ color: 'var(--accent)', flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {result.title}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 3, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                    <span style={{ color: 'var(--success)' }}>
                      <ArrowUpDown size={10} style={{ verticalAlign: -1 }} /> {result.seeds} seeds
                    </span>
                    <span>
                      <Users size={10} style={{ verticalAlign: -1 }} /> {result.leeches} leeches
                    </span>
                    <span>
                      <HardDrive size={10} style={{ verticalAlign: -1 }} /> {result.size}
                    </span>
                    <span className="badge badge-neutral" style={{ fontSize: 10 }}>{result.source}</span>
                    {result.category && <span className="badge badge-info" style={{ fontSize: 10 }}>{result.category}</span>}
                  </div>
                </div>
                <button
                  className="btn btn-primary"
                  style={{ fontSize: 12, padding: '6px 12px', flexShrink: 0 }}
                  onClick={() => handleAddMagnet(result.magnet)}
                >
                  <Download size={13} /> Download
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {showResults && searchResults.length === 0 && !searching && (
        <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-tertiary)', marginBottom: 28 }}>
          No results found for "{searchQuery}"
        </div>
      )}

      {/* Active Torrents */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600 }}>
          <Magnet size={16} style={{ verticalAlign: -2, marginRight: 6 }} />
          Active Torrents
        </h2>
        <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>{torrents.length} items</span>
      </div>

      {torrents.length > 0 ? (
        <div className="download-list">
          {torrents.map((t) => (
            <div key={t.info_hash}>
              <div
                className="card"
                style={{ display: 'flex', alignItems: 'center', gap: 14, cursor: 'pointer' }}
                onClick={() => setExpandedTorrent(expandedTorrent === t.info_hash ? null : t.info_hash)}
              >
                {expandedTorrent === t.info_hash ? <ChevronDown size={16} style={{ color: 'var(--text-tertiary)', flexShrink: 0 }} /> : <ChevronRight size={16} style={{ color: 'var(--text-tertiary)', flexShrink: 0 }} />}
                <Magnet size={18} style={{ color: 'var(--accent)', flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.name}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2, display: 'flex', gap: 10 }}>
                    <span style={{ color: 'var(--success)' }}>↓ {formatSpeed(t.download_speed || 0)}</span>
                    <span style={{ color: 'var(--warning)' }}>↑ {formatSpeed(t.upload_speed || 0)}</span>
                    <span>Seeds: {t.seeds}</span>
                    <span>Peers: {t.peers}</span>
                    <span>{formatSize(t.total_size || 0)}</span>
                  </div>
                  <div className="progress-bar" style={{ marginTop: 6 }}>
                    <div className="progress-bar-fill animated" style={{ width: `${t.progress * 100}%` }} />
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--accent)', fontWeight: 600, marginTop: 3 }}>
                    {(t.progress * 100).toFixed(1)}%
                  </div>
                </div>
              </div>

              {/* Expanded — Piece Map Visualization */}
              {expandedTorrent === t.info_hash && (
                <div style={{ padding: '12px 16px', background: 'var(--bg-tertiary)', borderRadius: '0 0 var(--radius-lg) var(--radius-lg)', marginTop: -1, borderTop: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>Piece Map</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                    {Array.from({ length: Math.min(200, 100) }, (_, i) => (
                      <div
                        key={i}
                        style={{
                          width: 6, height: 6, borderRadius: 1,
                          background: i / 100 < t.progress ? 'var(--accent)' : 'var(--bg-hover)',
                        }}
                      />
                    ))}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 8 }}>
                    Info Hash: <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10 }}>{t.info_hash}</span>
                  </div>
                </div>
              )}
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
