import { create } from 'zustand';

// ── Types ──
export type DownloadStatus = 'queued' | 'analyzing' | 'downloading' | 'paused' | 'muxing' | 'completed' | 'failed' | 'cancelled';
export type DownloadSource = 'direct' | 'ytdlp' | 'hls' | 'torrent' | 'telegram' | 'playlist';
export type ThemeId = 'dark-contrast' | 'standard-dark' | 'frosted-glass' | 'pure-light';
export type PageId = 'dashboard' | 'playlist' | 'torrent' | 'telegram' | 'history' | 'settings';

export interface DownloadItem {
  download_id: string;
  title: string;
  url: string;
  status: DownloadStatus;
  progress: number;
  speed: number;
  eta: number | null;
  file_size: number | null;
  downloaded_size: number;
  source: DownloadSource;
  quality: string | null;
  thumbnail_url: string | null;
  uploader: string | null;
  created_at: string | null;
  error_message?: string | null;
}

export interface TorrentItem {
  info_hash: string;
  name: string;
  state: string;
  progress: number;
  total_size: number;
  downloaded: number;
  uploaded: number;
  download_speed: number;
  upload_speed: number;
  seeds: number;
  peers: number;
  added_at: string | null;
}

export interface AppStats {
  total_downloads: number;
  completed: number;
  active: number;
  total_torrents: number;
  bytes_today: number;
  total_speed: number;
}

interface AppState {
  // Navigation
  currentPage: PageId;
  setCurrentPage: (page: PageId) => void;

  // Sidebar
  sidebarExpanded: boolean;
  toggleSidebar: () => void;

  // Theme
  theme: ThemeId;
  setTheme: (theme: ThemeId) => void;

  // Downloads
  downloads: DownloadItem[];
  setDownloads: (downloads: DownloadItem[]) => void;
  updateDownload: (id: string, updates: Partial<DownloadItem>) => void;
  addDownload: (download: DownloadItem) => void;
  removeDownload: (id: string) => void;

  // History
  history: DownloadItem[];
  setHistory: (history: DownloadItem[]) => void;

  // Torrents
  torrents: TorrentItem[];
  setTorrents: (torrents: TorrentItem[]) => void;

  // Stats
  stats: AppStats;
  setStats: (stats: Partial<AppStats>) => void;

  // URL input
  urlInput: string;
  setUrlInput: (url: string) => void;

  // Backend status
  backendConnected: boolean;
  setBackendConnected: (connected: boolean) => void;

  // Settings
  settings: Record<string, string>;
  setSettings: (settings: Record<string, string>) => void;
  updateSetting: (key: string, value: string) => void;
}

export const useAppStore = create<AppState>((set) => ({
  currentPage: 'dashboard',
  setCurrentPage: (page) => set({ currentPage: page }),

  sidebarExpanded: false,
  toggleSidebar: () => set((s) => ({ sidebarExpanded: !s.sidebarExpanded })),

  theme: (localStorage.getItem('deep-downloadr-theme') as ThemeId) || 'dark-contrast',
  setTheme: (theme) => {
    localStorage.setItem('deep-downloadr-theme', theme);
    document.documentElement.setAttribute('data-theme', theme);
    set({ theme });
  },

  downloads: [],
  setDownloads: (downloads) => set({ downloads }),
  updateDownload: (id, updates) =>
    set((s) => ({
      downloads: s.downloads.map((d) => (d.download_id === id ? { ...d, ...updates } : d)),
    })),
  addDownload: (download) => set((s) => ({ downloads: [download, ...s.downloads] })),
  removeDownload: (id) => set((s) => ({ downloads: s.downloads.filter((d) => d.download_id !== id) })),

  history: [],
  setHistory: (history) => set({ history }),

  torrents: [],
  setTorrents: (torrents) => set({ torrents }),

  stats: { total_downloads: 0, completed: 0, active: 0, total_torrents: 0, bytes_today: 0, total_speed: 0 },
  setStats: (stats) => set((s) => ({ stats: { ...s.stats, ...stats } })),

  urlInput: '',
  setUrlInput: (url) => set({ urlInput: url }),

  backendConnected: false,
  setBackendConnected: (connected) => set({ backendConnected: connected }),

  settings: {},
  setSettings: (settings) => set({ settings }),
  updateSetting: (key, value) => set((s) => ({ settings: { ...s.settings, [key]: value } })),
}));
