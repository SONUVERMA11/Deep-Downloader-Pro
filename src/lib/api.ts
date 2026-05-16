/** DEEP DOWNLOADR — API client for communicating with the Python backend */

const API_BASE = 'http://127.0.0.1:18920';

async function apiFetch<T = any>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'API request failed');
  }
  return res.json();
}

export const api = {
  health: () => apiFetch('/api/health'),

  // Downloads
  analyze: (url: string) => apiFetch('/api/analyze', { method: 'POST', body: JSON.stringify({ url }) }),
  download: (params: { url: string; format_id?: string; output_path?: string; quality?: string }) =>
    apiFetch('/api/download', { method: 'POST', body: JSON.stringify(params) }),
  pause: (download_id: string) => apiFetch('/api/pause', { method: 'POST', body: JSON.stringify({ download_id }) }),
  resume: (download_id: string) => apiFetch('/api/resume', { method: 'POST', body: JSON.stringify({ download_id }) }),
  cancel: (download_id: string) => apiFetch('/api/cancel', { method: 'POST', body: JSON.stringify({ download_id }) }),
  getDownloads: () => apiFetch('/api/downloads'),
  getHistory: () => apiFetch('/api/history'),
  getStats: () => apiFetch('/api/stats'),

  // Torrents
  searchTorrents: (query: string, category?: string) =>
    apiFetch('/api/torrent/search', { method: 'POST', body: JSON.stringify({ query, category }) }),
  addTorrent: (uri: string, save_path?: string) =>
    apiFetch('/api/torrent/add', { method: 'POST', body: JSON.stringify({ uri, save_path }) }),
  getTorrents: () => apiFetch('/api/torrents'),

  // Settings
  getSettings: () => apiFetch('/api/settings'),
  updateSettings: (settings: Record<string, any>) =>
    apiFetch('/api/settings', { method: 'POST', body: JSON.stringify({ settings }) }),
};

/** WebSocket connection manager */
export class WSClient {
  private ws: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private listeners: Map<string, Set<(data: any) => void>> = new Map();

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    this.ws = new WebSocket('ws://127.0.0.1:18920/api/ws');
    this.ws.onopen = () => this.emit('connected', {});
    this.ws.onclose = () => {
      this.emit('disconnected', {});
      this.reconnectTimer = setTimeout(() => this.connect(), 3000);
    };
    this.ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        this.emit(data.type, data);
      } catch {}
    };
  }

  disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
  }

  on(event: string, handler: (data: any) => void) {
    if (!this.listeners.has(event)) this.listeners.set(event, new Set());
    this.listeners.get(event)!.add(handler);
    return () => this.listeners.get(event)?.delete(handler);
  }

  private emit(event: string, data: any) {
    this.listeners.get(event)?.forEach((h) => h(data));
  }

  send(data: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }
}

export const wsClient = new WSClient();
