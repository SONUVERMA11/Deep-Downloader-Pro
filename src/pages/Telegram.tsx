import { MessageCircle, Key, Phone, Shield, Send, Loader2, Image, FileText, Film, Music, Download, RefreshCw, Search } from 'lucide-react';
import { useState } from 'react';

type AuthStep = 'credentials' | 'otp' | 'connected';

interface MediaItem {
  id: number;
  type: string;
  filename: string;
  size: number;
  date: string;
  chat_name: string;
}

export function Telegram() {
  const [authStep, setAuthStep] = useState<AuthStep>('credentials');
  const [apiId, setApiId] = useState('');
  const [apiHash, setApiHash] = useState('');
  const [phone, setPhone] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [mediaItems] = useState<MediaItem[]>([]);
  const [selectedItems, setSelectedItems] = useState<Set<number>>(new Set());

  const handleConnect = async () => {
    if (!apiId || !apiHash || !phone) {
      setError('All fields are required');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const res = await fetch('http://127.0.0.1:18920/api/telegram/auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_id: apiId, api_hash: apiHash, phone }),
      });
      const data = await res.json();
      if (data.success && data.needs_otp) {
        setAuthStep('otp');
      } else if (data.success) {
        setAuthStep('connected');
      } else {
        setError(data.detail || 'Connection failed');
      }
    } catch (err: any) {
      setError('Backend not running or Telegram auth endpoint not available. Make sure the backend is started.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async () => {
    if (!otpCode) return;
    setLoading(true);
    setError('');
    try {
      const res = await fetch('http://127.0.0.1:18920/api/telegram/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: otpCode }),
      });
      const data = await res.json();
      if (data.success) {
        setAuthStep('connected');
      } else {
        setError(data.detail || 'Invalid OTP code');
      }
    } catch (err: any) {
      setError('Verification failed');
    } finally {
      setLoading(false);
    }
  };

  const toggleSelect = (id: number) => {
    const next = new Set(selectedItems);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedItems(next);
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1073741824) return `${(bytes / 1048576).toFixed(1)} MB`;
    return `${(bytes / 1073741824).toFixed(1)} GB`;
  };

  const getMediaIcon = (type: string) => {
    switch (type) {
      case 'photo': return <Image size={16} style={{ color: 'var(--success)' }} />;
      case 'video': return <Film size={16} style={{ color: 'var(--accent)' }} />;
      case 'audio': return <Music size={16} style={{ color: 'var(--warning)' }} />;
      default: return <FileText size={16} style={{ color: 'var(--text-tertiary)' }} />;
    }
  };

  return (
    <div className="animate-in">
      <div className="page-header">
        <h1 className="page-title">Telegram</h1>
        <p className="page-subtitle">Browse and download media from Telegram chats, channels, and groups</p>
      </div>

      {/* Step 1: Credentials */}
      {authStep === 'credentials' && (
        <div style={{ maxWidth: 480, margin: '40px auto', textAlign: 'center' }}>
          <div style={{ width: 72, height: 72, borderRadius: 'var(--radius-xl)', background: 'var(--accent-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}>
            <MessageCircle size={32} style={{ color: 'var(--accent)' }} />
          </div>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Connect Telegram</h2>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 28 }}>
            Get your API credentials from my.telegram.org/apps (free). Your data stays local — nothing is transmitted.
          </p>

          {error && (
            <div style={{ fontSize: 12, color: 'var(--error)', marginBottom: 12, padding: '8px 12px', background: 'var(--error-subtle)', borderRadius: 'var(--radius-md)', textAlign: 'left' }}>
              {error}
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, textAlign: 'left' }}>
            <div>
              <label style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>
                <Key size={12} style={{ verticalAlign: -1, marginRight: 4 }} /> API ID
              </label>
              <input className="input" placeholder="Enter your API ID" value={apiId} onChange={(e) => setApiId(e.target.value)} />
            </div>
            <div>
              <label style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>
                <Shield size={12} style={{ verticalAlign: -1, marginRight: 4 }} /> API Hash
              </label>
              <input className="input" type="password" placeholder="Enter your API Hash" value={apiHash} onChange={(e) => setApiHash(e.target.value)} />
            </div>
            <div>
              <label style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>
                <Phone size={12} style={{ verticalAlign: -1, marginRight: 4 }} /> Phone Number
              </label>
              <input className="input" placeholder="+91 XXXXX XXXXX" value={phone} onChange={(e) => setPhone(e.target.value)} />
            </div>
            <button className="btn btn-primary" style={{ marginTop: 8 }} onClick={handleConnect} disabled={loading}>
              {loading ? <><Loader2 size={14} className="spin" /> Connecting...</> : <><Send size={14} /> Connect Account</>}
            </button>
          </div>

          <p style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 20 }}>
            🔒 Credentials are stored encrypted in your OS keychain. Local only.
          </p>
        </div>
      )}

      {/* Step 2: OTP Verification */}
      {authStep === 'otp' && (
        <div style={{ maxWidth: 400, margin: '60px auto', textAlign: 'center' }}>
          <div style={{ width: 72, height: 72, borderRadius: 'var(--radius-xl)', background: 'var(--success-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}>
            <Shield size={32} style={{ color: 'var(--success)' }} />
          </div>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Enter Verification Code</h2>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 24 }}>
            We've sent a code to your Telegram app. Enter it below.
          </p>

          {error && (
            <div style={{ fontSize: 12, color: 'var(--error)', marginBottom: 12, padding: '8px 12px', background: 'var(--error-subtle)', borderRadius: 'var(--radius-md)' }}>
              {error}
            </div>
          )}

          <input
            className="input"
            placeholder="Enter OTP code"
            value={otpCode}
            onChange={(e) => setOtpCode(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleVerifyOtp()}
            style={{ textAlign: 'center', fontSize: 24, letterSpacing: 8, fontWeight: 700, marginBottom: 16 }}
          />
          <button className="btn btn-primary" style={{ width: '100%' }} onClick={handleVerifyOtp} disabled={loading}>
            {loading ? <><Loader2 size={14} className="spin" /> Verifying...</> : 'Verify Code'}
          </button>
        </div>
      )}

      {/* Step 3: Connected — Media Browser */}
      {authStep === 'connected' && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
            <div className="badge badge-success"><span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--success)', display: 'inline-block' }} /> Connected</div>
            <button className="btn btn-ghost" style={{ fontSize: 12 }} onClick={() => setAuthStep('credentials')}>
              <RefreshCw size={12} /> Reconnect
            </button>
          </div>

          {/* Search */}
          <div className="url-input-container" style={{ marginBottom: 20 }}>
            <div style={{ padding: '0 8px', color: 'var(--text-tertiary)', display: 'flex', alignItems: 'center' }}>
              <Search size={18} />
            </div>
            <input
              className="input"
              placeholder="Search media across chats, channels, groups..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          {/* Media Grid */}
          {mediaItems.length > 0 ? (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{mediaItems.length} items • {selectedItems.size} selected</span>
                <button className="btn btn-primary" disabled={selectedItems.size === 0}>
                  <Download size={14} /> Download Selected ({selectedItems.size})
                </button>
              </div>
              <div className="download-list">
                {mediaItems.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => toggleSelect(item.id)}
                    className="card"
                    style={{
                      display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer',
                      border: selectedItems.has(item.id) ? '1px solid var(--accent)' : undefined,
                      background: selectedItems.has(item.id) ? 'var(--accent-subtle)' : undefined,
                    }}
                  >
                    {getMediaIcon(item.type)}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.filename}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{item.chat_name} • {formatSize(item.size)} • {item.date}</div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="empty-state">
              <MessageCircle className="empty-state-icon" size={64} />
              <div className="empty-state-title">No media found</div>
              <div className="empty-state-text">Connected successfully! Browse your chats or search for media to start downloading.</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
