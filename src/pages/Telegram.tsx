import { MessageCircle, Key, Phone, Shield } from 'lucide-react';
import { useState } from 'react';

type AuthStep = 'credentials' | 'phone' | 'session' | 'connected';

export function Telegram() {
  const [authStep] = useState<AuthStep>('credentials');

  return (
    <div className="animate-in">
      <div className="page-header">
        <h1 className="page-title">Telegram</h1>
        <p className="page-subtitle">Browse and download media from Telegram chats, channels, and groups</p>
      </div>

      {authStep === 'credentials' && (
        <div style={{ maxWidth: 480, margin: '40px auto', textAlign: 'center' }}>
          <div style={{ width: 72, height: 72, borderRadius: 'var(--radius-xl)', background: 'var(--accent-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}>
            <MessageCircle size={32} style={{ color: 'var(--accent)' }} />
          </div>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Connect Telegram</h2>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 28 }}>
            Get your API credentials from my.telegram.org/apps (free). Your data stays local — nothing is transmitted.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, textAlign: 'left' }}>
            <div>
              <label style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>
                <Key size={12} style={{ verticalAlign: -1, marginRight: 4 }} /> API ID
              </label>
              <input className="input" placeholder="Enter your API ID" />
            </div>
            <div>
              <label style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>
                <Shield size={12} style={{ verticalAlign: -1, marginRight: 4 }} /> API Hash
              </label>
              <input className="input" type="password" placeholder="Enter your API Hash" />
            </div>
            <div>
              <label style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>
                <Phone size={12} style={{ verticalAlign: -1, marginRight: 4 }} /> Phone Number
              </label>
              <input className="input" placeholder="+91 XXXXX XXXXX" />
            </div>
            <button className="btn btn-primary" style={{ marginTop: 8 }}>Connect Account</button>
          </div>

          <p style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 20 }}>
            🔒 Credentials are stored encrypted in your OS keychain. Local only.
          </p>
        </div>
      )}
    </div>
  );
}
