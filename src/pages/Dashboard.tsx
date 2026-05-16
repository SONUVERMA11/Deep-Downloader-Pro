import { useState } from 'react';
import { useAppStore } from '../store/useAppStore';
import { DownloadCard } from '../components/DownloadCard';
import { Search, Link, ArrowDownToLine, Zap, TrendingUp, CheckCircle2, Clock } from 'lucide-react';
import { api } from '../lib/api';

export function Dashboard() {
  const { downloads, urlInput, setUrlInput, stats } = useAppStore();
  const [analyzing, setAnalyzing] = useState(false);

  const handleAnalyze = async () => {
    if (!urlInput.trim()) return;
    setAnalyzing(true);
    try {
      const result = await api.analyze(urlInput);
      console.log('Analysis result:', result);
      // TODO: Open format picker modal
    } catch (err) {
      console.error('Analysis failed:', err);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleAnalyze();
  };

  const activeDownloads = downloads.filter(d => ['downloading', 'queued', 'paused', 'analyzing', 'muxing'].includes(d.status));

  return (
    <div className="animate-in">
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">Paste any URL to start downloading</p>
      </div>

      {/* URL Input */}
      <div className="url-input-container" style={{ marginBottom: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', padding: '0 8px', color: 'var(--text-tertiary)' }}>
          <Link size={18} />
        </div>
        <input
          className="input"
          type="text"
          placeholder="Paste a URL — YouTube, Instagram, Torrent, M3U8, or any direct link..."
          value={urlInput}
          onChange={(e) => setUrlInput(e.target.value)}
          onKeyDown={handleKeyDown}
          id="url-input"
        />
        <button
          className="btn btn-primary"
          onClick={handleAnalyze}
          disabled={analyzing || !urlInput.trim()}
          style={{ minWidth: 120, flexShrink: 0 }}
        >
          {analyzing ? (
            <><Zap size={14} className="spin" /> Analyzing...</>
          ) : (
            <><Search size={14} /> Analyze</>
          )}
        </button>
      </div>

      {/* Quick Stats */}
      <div className="grid-3" style={{ marginBottom: 28 }}>
        <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ width: 42, height: 42, borderRadius: 'var(--radius-md)', background: 'var(--accent-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <TrendingUp size={20} style={{ color: 'var(--accent)' }} />
          </div>
          <div>
            <div style={{ fontSize: 22, fontWeight: 700 }}>{stats.active}</div>
            <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>Active Downloads</div>
          </div>
        </div>
        <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ width: 42, height: 42, borderRadius: 'var(--radius-md)', background: 'var(--success-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <CheckCircle2 size={20} style={{ color: 'var(--success)' }} />
          </div>
          <div>
            <div style={{ fontSize: 22, fontWeight: 700 }}>{stats.completed}</div>
            <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>Completed</div>
          </div>
        </div>
        <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ width: 42, height: 42, borderRadius: 'var(--radius-md)', background: 'var(--info-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Clock size={20} style={{ color: 'var(--info)' }} />
          </div>
          <div>
            <div style={{ fontSize: 22, fontWeight: 700 }}>{stats.total_downloads}</div>
            <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>Total Downloads</div>
          </div>
        </div>
      </div>

      {/* Active Downloads */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600 }}>
          <ArrowDownToLine size={18} style={{ verticalAlign: -3, marginRight: 8 }} />
          Active Downloads
        </h2>
        <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>{activeDownloads.length} items</span>
      </div>

      {activeDownloads.length > 0 ? (
        <div className="download-list">
          {activeDownloads.map((item) => (
            <DownloadCard
              key={item.download_id}
              item={item}
              onPause={(id) => api.pause(id).catch(console.error)}
              onResume={(id) => api.resume(id).catch(console.error)}
              onCancel={(id) => api.cancel(id).catch(console.error)}
            />
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <ArrowDownToLine className="empty-state-icon" size={64} />
          <div className="empty-state-title">No active downloads</div>
          <div className="empty-state-text">Paste a URL above to start downloading media from YouTube, Instagram, Telegram, or any supported source.</div>
        </div>
      )}
    </div>
  );
}
