import { useAppStore } from '../store/useAppStore';
import { ArrowDown, HardDrive, Wifi, WifiOff } from 'lucide-react';

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function formatSpeed(bytesPerSec: number): string {
  return formatBytes(bytesPerSec) + '/s';
}

export function StatusBar() {
  const { stats, backendConnected, sidebarExpanded, downloads } = useAppStore();
  const activeCount = downloads.filter((d) => d.status === 'downloading').length;
  const totalSpeed = downloads.reduce((sum, d) => sum + (d.status === 'downloading' ? d.speed : 0), 0);

  return (
    <div className={`status-bar ${sidebarExpanded ? 'sidebar-expanded' : ''}`}>
      <div className="status-item">
        <span className={`status-dot ${backendConnected ? 'green' : 'red'}`} />
        {backendConnected ? (
          <><Wifi size={12} /> Backend</>
        ) : (
          <><WifiOff size={12} /> Offline</>
        )}
      </div>

      <div className="status-item">
        <ArrowDown size={12} />
        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
          {formatSpeed(totalSpeed)}
        </span>
      </div>

      <div className="status-item">
        <span>{activeCount} active</span>
      </div>

      <div className="status-item" style={{ marginLeft: 'auto' }}>
        <HardDrive size={12} />
        <span>Today: {formatBytes(stats.bytes_today)}</span>
      </div>
    </div>
  );
}
