import { type DownloadItem } from '../store/useAppStore';
import { Pause, Play, X, RotateCcw, Check, AlertTriangle, Loader } from 'lucide-react';

function formatBytes(bytes: number): string {
  if (!bytes || bytes === 0) return '—';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function formatSpeed(bytesPerSec: number): string {
  if (!bytesPerSec) return '—';
  return formatBytes(bytesPerSec) + '/s';
}

function formatEta(seconds: number | null): string {
  if (!seconds || seconds <= 0) return '—';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

const statusBadge: Record<string, { class: string; icon: React.ComponentType<any>; label: string }> = {
  downloading: { class: 'badge-info', icon: Loader, label: 'Downloading' },
  queued: { class: 'badge-neutral', icon: Loader, label: 'Queued' },
  paused: { class: 'badge-warning', icon: Pause, label: 'Paused' },
  completed: { class: 'badge-success', icon: Check, label: 'Done' },
  failed: { class: 'badge-error', icon: AlertTriangle, label: 'Failed' },
  cancelled: { class: 'badge-neutral', icon: X, label: 'Cancelled' },
  analyzing: { class: 'badge-info', icon: Loader, label: 'Analyzing' },
  muxing: { class: 'badge-info', icon: Loader, label: 'Muxing' },
};

interface Props {
  item: DownloadItem;
  onPause?: (id: string) => void;
  onResume?: (id: string) => void;
  onCancel?: (id: string) => void;
  onRetry?: (id: string) => void;
}

export function DownloadCard({ item, onPause, onResume, onCancel, onRetry }: Props) {
  const badge = statusBadge[item.status] || statusBadge.queued;
  const BadgeIcon = badge.icon;

  return (
    <div className="download-card animate-in">
      {item.thumbnail_url ? (
        <img className="download-card-thumb" src={item.thumbnail_url} alt="" />
      ) : (
        <div className="download-card-thumb" />
      )}

      <div className="download-card-info">
        <div className="download-card-title" title={item.title}>{item.title}</div>
        <div className="download-card-meta">
          {item.uploader && <span>{item.uploader} • </span>}
          {item.quality && <span>{item.quality} • </span>}
          {item.file_size ? formatBytes(item.file_size) : ''}
        </div>
        {(item.status === 'downloading' || item.status === 'paused') && (
          <div className="progress-bar">
            <div
              className={`progress-bar-fill ${item.status === 'downloading' ? 'animated' : ''}`}
              style={{ width: `${item.progress}%` }}
            />
          </div>
        )}
      </div>

      <div className="download-card-stats">
        {item.status === 'downloading' && (
          <>
            <span className="download-card-speed">{formatSpeed(item.speed)}</span>
            <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{formatEta(item.eta)}</span>
          </>
        )}
        <span className={`badge ${badge.class}`}>
          <BadgeIcon size={10} />
          {badge.label}
        </span>
      </div>

      <div className="download-card-actions">
        {item.status === 'downloading' && (
          <button className="btn-icon" onClick={() => onPause?.(item.download_id)} title="Pause">
            <Pause size={16} />
          </button>
        )}
        {item.status === 'paused' && (
          <button className="btn-icon" onClick={() => onResume?.(item.download_id)} title="Resume">
            <Play size={16} />
          </button>
        )}
        {item.status === 'failed' && (
          <button className="btn-icon" onClick={() => onRetry?.(item.download_id)} title="Retry">
            <RotateCcw size={16} />
          </button>
        )}
        {['downloading', 'queued', 'paused', 'analyzing'].includes(item.status) && (
          <button className="btn-icon" onClick={() => onCancel?.(item.download_id)} title="Cancel">
            <X size={16} />
          </button>
        )}
      </div>
    </div>
  );
}
