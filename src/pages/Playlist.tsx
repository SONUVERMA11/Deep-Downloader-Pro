import { ListVideo, Plus, RefreshCw } from 'lucide-react';

export function Playlist() {
  return (
    <div className="animate-in">
      <div className="page-header">
        <h1 className="page-title">Playlists & Channels</h1>
        <p className="page-subtitle">Download entire playlists, channels, and RSS feeds</p>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        <button className="btn btn-primary"><Plus size={14} /> Add Playlist</button>
        <button className="btn btn-secondary"><RefreshCw size={14} /> Sync All</button>
      </div>

      <div className="empty-state">
        <ListVideo className="empty-state-icon" size={64} />
        <div className="empty-state-title">No playlists tracked</div>
        <div className="empty-state-text">Add a YouTube playlist, channel URL, RSS feed, or IPTV playlist to get started. Enable auto-sync to catch new content automatically.</div>
      </div>
    </div>
  );
}
