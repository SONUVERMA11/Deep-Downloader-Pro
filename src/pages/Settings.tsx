import { useAppStore, type ThemeId } from '../store/useAppStore';
import { Settings as SettingsIcon, Palette, Download, Gauge, Film, Magnet, MessageCircle, Clock, Wrench, FolderOpen } from 'lucide-react';
import { useState } from 'react';

const themes: { id: ThemeId; name: string; desc: string; preview: string }[] = [
  { id: 'dark-contrast', name: 'Dark Contrast+', desc: 'Near-black with electric blue', preview: '#0d0e12' },
  { id: 'standard-dark', name: 'Standard Dark', desc: 'iOS-style dark mode', preview: '#1c1c1e' },
  { id: 'frosted-glass', name: 'Frosted Glass', desc: 'Translucent blur panels', preview: '#121218' },
  { id: 'pure-light', name: 'Pure Light', desc: 'Clean light mode', preview: '#f2f2f7' },
];

const sections = [
  { id: 'general', label: 'General', icon: SettingsIcon },
  { id: 'downloads', label: 'Downloads', icon: Download },
  { id: 'speed', label: 'Speed', icon: Gauge },
  { id: 'themes', label: 'Themes', icon: Palette },
  { id: 'formats', label: 'Formats', icon: Film },
  { id: 'torrent', label: 'Torrent', icon: Magnet },
  { id: 'telegram', label: 'Telegram', icon: MessageCircle },
  { id: 'scheduler', label: 'Scheduler', icon: Clock },
  { id: 'advanced', label: 'Advanced', icon: Wrench },
];

export function Settings() {
  const { theme, setTheme, settings } = useAppStore();
  const [activeSection, setActiveSection] = useState('themes');

  return (
    <div className="animate-in">
      <div className="page-header">
        <h1 className="page-title">Settings</h1>
        <p className="page-subtitle">Configure DEEP DOWNLOADR preferences</p>
      </div>

      <div style={{ display: 'flex', gap: 24 }}>
        {/* Settings Navigation */}
        <div style={{ width: 180, flexShrink: 0 }}>
          {sections.map((s) => (
            <div
              key={s.id}
              onClick={() => setActiveSection(s.id)}
              className={`sidebar-item ${activeSection === s.id ? 'active' : ''}`}
              style={{ borderRadius: 'var(--radius-md)', marginBottom: 2 }}
            >
              <s.icon size={16} className="sidebar-item-icon" />
              <span style={{ fontSize: 13, fontWeight: 500, opacity: 1 }}>{s.label}</span>
            </div>
          ))}
        </div>

        {/* Settings Content */}
        <div style={{ flex: 1 }}>
          {activeSection === 'themes' && (
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Theme</h3>
              <div className="grid-2">
                {themes.map((t) => (
                  <div
                    key={t.id}
                    className="card"
                    onClick={() => setTheme(t.id)}
                    style={{
                      cursor: 'pointer',
                      border: theme === t.id ? '2px solid var(--accent)' : undefined,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <div style={{ width: 40, height: 40, borderRadius: 'var(--radius-md)', background: t.preview, border: '1px solid var(--border)' }} />
                      <div>
                        <div style={{ fontWeight: 600, fontSize: 14 }}>{t.name}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{t.desc}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeSection === 'downloads' && (
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Downloads</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 4 }}>
                    <FolderOpen size={12} /> Default Save Path
                  </label>
                  <input className="input" defaultValue={settings['download.save_path'] || '~/Downloads/DEEP DOWNLOADR'} />
                </div>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 6, display: 'block' }}>Filename Template</label>
                  <input className="input" defaultValue={settings['download.filename_template'] || '{title}.{ext}'} />
                  <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4 }}>
                    Available: {'{title}'}, {'{uploader}'}, {'{resolution}'}, {'{upload_date}'}, {'{ext}'}
                  </div>
                </div>
                <div className="grid-2">
                  <div>
                    <label style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 6, display: 'block' }}>Concurrent Downloads</label>
                    <input className="input" type="number" min={1} max={10} defaultValue={settings['download.concurrent'] || '3'} />
                  </div>
                  <div>
                    <label style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 6, display: 'block' }}>Retry Attempts</label>
                    <input className="input" type="number" min={0} max={10} defaultValue={settings['download.retry_attempts'] || '3'} />
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeSection === 'general' && (
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>General</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Launch at login, minimize to tray, language preferences, and update settings.</p>
            </div>
          )}

          {!['themes', 'downloads', 'general'].includes(activeSection) && (
            <div className="empty-state" style={{ padding: 40 }}>
              <SettingsIcon className="empty-state-icon" size={48} />
              <div className="empty-state-title">{sections.find(s => s.id === activeSection)?.label} Settings</div>
              <div className="empty-state-text">Configuration options for this section will be available in Phase 9.</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
