import { useAppStore, type ThemeId } from '../store/useAppStore';
import { Settings as SettingsIcon, Palette, Download, Gauge, Film, Magnet, MessageCircle, Clock, Wrench, FolderOpen, Save, RefreshCw } from 'lucide-react';
import { useState, useEffect } from 'react';
import { api } from '../lib/api';

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

function SettingRow({ label, description, children }: { label: string; description?: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid var(--border-subtle)' }}>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 13, fontWeight: 500 }}>{label}</div>
        {description && <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2 }}>{description}</div>}
      </div>
      <div style={{ flexShrink: 0, marginLeft: 16 }}>{children}</div>
    </div>
  );
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <div
      onClick={() => onChange(!checked)}
      style={{
        width: 40, height: 22, borderRadius: 11, cursor: 'pointer',
        background: checked ? 'var(--accent)' : 'var(--bg-hover)',
        padding: 2, transition: 'background 0.2s ease',
        display: 'flex', alignItems: 'center',
      }}
    >
      <div style={{
        width: 18, height: 18, borderRadius: '50%', background: '#fff',
        transition: 'transform 0.2s ease',
        transform: checked ? 'translateX(18px)' : 'translateX(0)',
        boxShadow: '0 1px 3px rgba(0,0,0,.3)',
      }} />
    </div>
  );
}

export function Settings() {
  const { theme, setTheme } = useAppStore();
  const [activeSection, setActiveSection] = useState('themes');
  const [saving, setSaving] = useState(false);
  const [localSettings, setLocalSettings] = useState<Record<string, string>>({
    'download.save_path': '~/Downloads/DEEP DOWNLOADR',
    'download.concurrent': '3',
    'download.retry_attempts': '3',
    'download.filename_template': '{title}.{ext}',
    'speed.bandwidth_limit': '0',
    'speed.connections_per_download': '16',
    'format.default_quality': 'best',
    'format.default_container': 'mp4',
    'format.subtitle_language': 'en',
    'torrent.listen_port_start': '6881',
    'torrent.listen_port_end': '6889',
    'torrent.max_upload_speed': '0',
    'torrent.max_connections': '200',
    'torrent.seed_ratio_limit': '2.0',
    'torrent.dht_enabled': 'true',
    'torrent.pex_enabled': 'true',
    'general.launch_at_login': 'false',
    'general.minimize_to_tray': 'true',
    'advanced.debug_log': 'false',
  });

  useEffect(() => {
    api.getSettings().then((res: any) => {
      if (res.settings) {
        const merged = { ...localSettings };
        for (const [key, val] of Object.entries(res.settings)) {
          merged[key] = (val as any).value || '';
        }
        setLocalSettings(merged);
      }
    }).catch(() => {});
  }, []);

  const updateSetting = (key: string, value: string) => {
    setLocalSettings(prev => ({ ...prev, [key]: value }));
  };

  const saveSettings = async () => {
    setSaving(true);
    try {
      await api.updateSettings(localSettings);
    } catch (err) {
      console.error('Save failed:', err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="animate-in">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">Settings</h1>
          <p className="page-subtitle">Configure DEEP DOWNLOADR preferences</p>
        </div>
        {activeSection !== 'themes' && (
          <button className="btn btn-primary" onClick={saveSettings} disabled={saving} style={{ fontSize: 12 }}>
            {saving ? <><RefreshCw size={13} className="spin" /> Saving...</> : <><Save size={13} /> Save Changes</>}
          </button>
        )}
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

          {activeSection === 'general' && (
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>General</h3>
              <SettingRow label="Launch at Login" description="Automatically start DEEP DOWNLOADR when your computer starts">
                <Toggle checked={localSettings['general.launch_at_login'] === 'true'} onChange={(v) => updateSetting('general.launch_at_login', String(v))} />
              </SettingRow>
              <SettingRow label="Minimize to Tray" description="Keep running in system tray when window is closed">
                <Toggle checked={localSettings['general.minimize_to_tray'] === 'true'} onChange={(v) => updateSetting('general.minimize_to_tray', String(v))} />
              </SettingRow>
              <SettingRow label="Auto-update yt-dlp" description="Automatically check for yt-dlp updates on launch">
                <Toggle checked={true} onChange={() => {}} />
              </SettingRow>
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
                  <input className="input" value={localSettings['download.save_path']} onChange={(e) => updateSetting('download.save_path', e.target.value)} />
                </div>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 6, display: 'block' }}>Filename Template</label>
                  <input className="input" value={localSettings['download.filename_template']} onChange={(e) => updateSetting('download.filename_template', e.target.value)} />
                  <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4 }}>
                    Available: {'{title}'}, {'{uploader}'}, {'{resolution}'}, {'{upload_date}'}, {'{ext}'}
                  </div>
                </div>
                <div className="grid-2">
                  <div>
                    <label style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 6, display: 'block' }}>Concurrent Downloads</label>
                    <input className="input" type="number" min={1} max={10} value={localSettings['download.concurrent']} onChange={(e) => updateSetting('download.concurrent', e.target.value)} />
                  </div>
                  <div>
                    <label style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 6, display: 'block' }}>Retry Attempts</label>
                    <input className="input" type="number" min={0} max={10} value={localSettings['download.retry_attempts']} onChange={(e) => updateSetting('download.retry_attempts', e.target.value)} />
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeSection === 'speed' && (
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Speed & Bandwidth</h3>
              <SettingRow label="Global Bandwidth Limit" description="0 = unlimited. Set in KB/s.">
                <input className="input" type="number" min={0} style={{ width: 120, textAlign: 'right' }} value={localSettings['speed.bandwidth_limit']} onChange={(e) => updateSetting('speed.bandwidth_limit', e.target.value)} />
              </SettingRow>
              <SettingRow label="Connections per Download" description="Number of parallel connections per file (8-32)">
                <input className="input" type="number" min={1} max={32} style={{ width: 80, textAlign: 'right' }} value={localSettings['speed.connections_per_download']} onChange={(e) => updateSetting('speed.connections_per_download', e.target.value)} />
              </SettingRow>
            </div>
          )}

          {activeSection === 'formats' && (
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Default Formats</h3>
              <SettingRow label="Default Quality">
                <select className="input" style={{ width: 160 }} value={localSettings['format.default_quality']} onChange={(e) => updateSetting('format.default_quality', e.target.value)}>
                  <option value="best">Best Available</option>
                  <option value="1080p">1080p</option>
                  <option value="720p">720p</option>
                  <option value="480p">480p</option>
                  <option value="360p">360p</option>
                  <option value="audio">Audio Only</option>
                </select>
              </SettingRow>
              <SettingRow label="Default Container">
                <select className="input" style={{ width: 120 }} value={localSettings['format.default_container']} onChange={(e) => updateSetting('format.default_container', e.target.value)}>
                  <option value="mp4">MP4</option>
                  <option value="mkv">MKV</option>
                  <option value="webm">WebM</option>
                  <option value="mp3">MP3 (Audio)</option>
                  <option value="m4a">M4A (Audio)</option>
                </select>
              </SettingRow>
              <SettingRow label="Subtitle Language" description="Default language for subtitles">
                <input className="input" style={{ width: 80, textAlign: 'right' }} value={localSettings['format.subtitle_language']} onChange={(e) => updateSetting('format.subtitle_language', e.target.value)} />
              </SettingRow>
            </div>
          )}

          {activeSection === 'torrent' && (
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Torrent Settings</h3>
              <SettingRow label="Listen Port Range" description="Ports for incoming torrent connections">
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <input className="input" type="number" style={{ width: 80, textAlign: 'right' }} value={localSettings['torrent.listen_port_start']} onChange={(e) => updateSetting('torrent.listen_port_start', e.target.value)} />
                  <span style={{ color: 'var(--text-tertiary)' }}>–</span>
                  <input className="input" type="number" style={{ width: 80, textAlign: 'right' }} value={localSettings['torrent.listen_port_end']} onChange={(e) => updateSetting('torrent.listen_port_end', e.target.value)} />
                </div>
              </SettingRow>
              <SettingRow label="Max Upload Speed" description="0 = unlimited (KB/s)">
                <input className="input" type="number" min={0} style={{ width: 100, textAlign: 'right' }} value={localSettings['torrent.max_upload_speed']} onChange={(e) => updateSetting('torrent.max_upload_speed', e.target.value)} />
              </SettingRow>
              <SettingRow label="Max Connections">
                <input className="input" type="number" min={1} style={{ width: 100, textAlign: 'right' }} value={localSettings['torrent.max_connections']} onChange={(e) => updateSetting('torrent.max_connections', e.target.value)} />
              </SettingRow>
              <SettingRow label="Seed Ratio Limit" description="Stop seeding after reaching this ratio">
                <input className="input" type="number" min={0} step={0.1} style={{ width: 80, textAlign: 'right' }} value={localSettings['torrent.seed_ratio_limit']} onChange={(e) => updateSetting('torrent.seed_ratio_limit', e.target.value)} />
              </SettingRow>
              <SettingRow label="Enable DHT" description="Distributed Hash Table for peer discovery">
                <Toggle checked={localSettings['torrent.dht_enabled'] === 'true'} onChange={(v) => updateSetting('torrent.dht_enabled', String(v))} />
              </SettingRow>
              <SettingRow label="Enable PEX" description="Peer Exchange protocol">
                <Toggle checked={localSettings['torrent.pex_enabled'] === 'true'} onChange={(v) => updateSetting('torrent.pex_enabled', String(v))} />
              </SettingRow>
            </div>
          )}

          {activeSection === 'telegram' && (
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Telegram</h3>
              <SettingRow label="Auto-resume Downloads" description="Automatically resume interrupted Telegram downloads">
                <Toggle checked={true} onChange={() => {}} />
              </SettingRow>
              <SettingRow label="Concurrent Telegram Downloads" description="Max parallel downloads from Telegram">
                <input className="input" type="number" min={1} max={5} style={{ width: 80, textAlign: 'right' }} defaultValue={3} />
              </SettingRow>
              <SettingRow label="Download Large Files" description="Allow downloading files larger than 2GB">
                <Toggle checked={true} onChange={() => {}} />
              </SettingRow>
            </div>
          )}

          {activeSection === 'scheduler' && (
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Scheduler</h3>
              <SettingRow label="Enable Scheduler" description="Schedule downloads for specific times">
                <Toggle checked={false} onChange={() => {}} />
              </SettingRow>
              <SettingRow label="Speed Limit During Schedule" description="Limit bandwidth during working hours (KB/s)">
                <input className="input" type="number" min={0} style={{ width: 100, textAlign: 'right' }} defaultValue={0} />
              </SettingRow>
              <SettingRow label="Schedule Active Hours" description="Downloads run at full speed outside these hours">
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 12 }}>
                  <input className="input" type="time" style={{ width: 100 }} defaultValue="09:00" />
                  <span style={{ color: 'var(--text-tertiary)' }}>to</span>
                  <input className="input" type="time" style={{ width: 100 }} defaultValue="17:00" />
                </div>
              </SettingRow>
            </div>
          )}

          {activeSection === 'advanced' && (
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Advanced</h3>
              <SettingRow label="Debug Logging" description="Enable verbose logging to ~/.deep-downloadr/logs/">
                <Toggle checked={localSettings['advanced.debug_log'] === 'true'} onChange={(v) => updateSetting('advanced.debug_log', String(v))} />
              </SettingRow>
              <SettingRow label="Duplicate Detection" description="Automatically detect and skip duplicate files">
                <Toggle checked={true} onChange={() => {}} />
              </SettingRow>
              <SettingRow label="Folder Watcher" description="Monitor folders for .torrent and .deepdl files">
                <Toggle checked={false} onChange={() => {}} />
              </SettingRow>
              <SettingRow label="Clear Database" description="Reset all download history and settings">
                <button className="btn btn-danger" style={{ fontSize: 12, padding: '4px 12px' }}>Reset</button>
              </SettingRow>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
