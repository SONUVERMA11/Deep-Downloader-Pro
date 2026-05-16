import { useState, useEffect } from 'react';
import {
  X, Download, Film, Music, Subtitles, MonitorPlay,
  FileVideo, FileAudio, Info, Sparkles, Check
} from 'lucide-react';

interface FormatOption {
  format_id: string;
  resolution: string;
  ext: string;
  has_video: boolean;
  has_audio: boolean;
  codec_family: string;
  audio_codec_family: string;
  filesize_str: string;
  filesize: number | null;
  fps: number | null;
  tbr: number | null;
  abr: number | null;
  is_hdr: boolean;
  format_note: string;
}

interface AnalysisResult {
  title: string;
  thumbnail: string;
  duration: number | null;
  uploader: string;
  formats: FormatOption[];
  video_formats: FormatOption[];
  audio_formats: FormatOption[];
  combined_formats: FormatOption[];
  subtitles: Record<string, any[]>;
}

interface FormatPickerProps {
  result: AnalysisResult;
  url: string;
  onClose: () => void;
  onDownload: (formatId: string | null, quality: string) => void;
}

export function FormatPicker({ result, onClose, onDownload }: FormatPickerProps) {
  const [tab, setTab] = useState<'video' | 'audio' | 'combined'>('video');
  const [selectedFormat, setSelectedFormat] = useState<string | null>(null);
  const [embedMeta, setEmbedMeta] = useState(true);
  const [embedThumb, setEmbedThumb] = useState(true);

  // Auto-select best format
  useEffect(() => {
    const combined = result.combined_formats;
    if (combined.length > 0) {
      setTab('combined');
      setSelectedFormat(combined[0].format_id);
    } else if (result.video_formats.length > 0) {
      setTab('video');
      setSelectedFormat(result.video_formats[0].format_id);
    }
  }, [result]);

  const formatDuration = (s: number | null) => {
    if (!s) return '';
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = Math.floor(s % 60);
    return h > 0 ? `${h}:${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}` : `${m}:${sec.toString().padStart(2, '0')}`;
  };

  const currentFormats = tab === 'video' ? result.video_formats
    : tab === 'audio' ? result.audio_formats
    : result.combined_formats;

  // Deduplicate by resolution, keep best quality per resolution
  const deduped = currentFormats.reduce<FormatOption[]>((acc, fmt) => {
    const key = tab === 'audio' ? `${fmt.abr || 0}-${fmt.audio_codec_family}` : `${fmt.resolution}-${fmt.codec_family}`;
    if (!acc.find(f => {
      const fKey = tab === 'audio' ? `${f.abr || 0}-${f.audio_codec_family}` : `${f.resolution}-${f.codec_family}`;
      return fKey === key;
    })) {
      acc.push(fmt);
    }
    return acc;
  }, []);

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-content" style={{ maxWidth: 680, maxHeight: '85vh' }}>
        {/* Header */}
        <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
          {result.thumbnail && (
            <img
              src={result.thumbnail}
              alt=""
              style={{ width: 140, height: 80, objectFit: 'cover', borderRadius: 'var(--radius-md)', flexShrink: 0 }}
            />
          )}
          <div style={{ flex: 1, minWidth: 0 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {result.title}
            </h2>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              {result.uploader && <span>{result.uploader}</span>}
              {result.duration && <span>{formatDuration(result.duration)}</span>}
              <span>{result.formats.length} formats</span>
              {Object.keys(result.subtitles).length > 0 && (
                <span><Subtitles size={11} style={{ verticalAlign: -1 }} /> {Object.keys(result.subtitles).length} subtitles</span>
              )}
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-tertiary)', padding: 4 }}>
            <X size={20} />
          </button>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 2, marginBottom: 16, background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', padding: 3 }}>
          <button
            className={`btn ${tab === 'combined' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setTab('combined')}
            style={{ flex: 1, fontSize: 12, padding: '6px 0' }}
          >
            <MonitorPlay size={13} style={{ marginRight: 4 }} /> Video+Audio ({result.combined_formats.length})
          </button>
          <button
            className={`btn ${tab === 'video' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setTab('video')}
            style={{ flex: 1, fontSize: 12, padding: '6px 0' }}
          >
            <Film size={13} style={{ marginRight: 4 }} /> Video Only ({result.video_formats.length})
          </button>
          <button
            className={`btn ${tab === 'audio' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setTab('audio')}
            style={{ flex: 1, fontSize: 12, padding: '6px 0' }}
          >
            <Music size={13} style={{ marginRight: 4 }} /> Audio ({result.audio_formats.length})
          </button>
        </div>

        {/* Format List */}
        <div style={{ maxHeight: 320, overflowY: 'auto', marginBottom: 16 }}>
          {deduped.length > 0 ? deduped.map((fmt) => (
            <div
              key={fmt.format_id}
              onClick={() => setSelectedFormat(fmt.format_id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '10px 12px',
                borderRadius: 'var(--radius-md)',
                cursor: 'pointer',
                marginBottom: 4,
                background: selectedFormat === fmt.format_id ? 'var(--accent-subtle)' : 'transparent',
                border: selectedFormat === fmt.format_id ? '1px solid var(--accent)' : '1px solid transparent',
                transition: 'all 0.15s ease',
              }}
            >
              <div style={{ width: 20, height: 20, borderRadius: '50%', border: `2px solid ${selectedFormat === fmt.format_id ? 'var(--accent)' : 'var(--border)'}`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                {selectedFormat === fmt.format_id && <Check size={12} style={{ color: 'var(--accent)' }} />}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  {fmt.has_video ? <FileVideo size={13} style={{ color: 'var(--accent)', flexShrink: 0 }} /> : <FileAudio size={13} style={{ color: 'var(--success)', flexShrink: 0 }} />}
                  <span style={{ fontWeight: 600, fontSize: 13 }}>
                    {fmt.has_video ? fmt.resolution : `${fmt.abr || '?'}kbps`}
                  </span>
                  {fmt.is_hdr && <span style={{ fontSize: 9, padding: '1px 5px', borderRadius: 4, background: 'linear-gradient(135deg, #f59e0b, #ef4444)', color: '#fff', fontWeight: 700 }}>HDR</span>}
                  {fmt.fps && fmt.fps > 30 && <span style={{ fontSize: 10, color: 'var(--accent)', fontWeight: 600 }}>{fmt.fps}fps</span>}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2 }}>
                  {fmt.has_video ? fmt.codec_family : fmt.audio_codec_family} • .{fmt.ext} • {fmt.filesize_str}
                  {fmt.format_note && ` • ${fmt.format_note}`}
                </div>
              </div>
            </div>
          )) : (
            <div style={{ textAlign: 'center', padding: 30, color: 'var(--text-tertiary)', fontSize: 13 }}>
              <Info size={24} style={{ marginBottom: 8, opacity: 0.5 }} />
              <div>No {tab} formats available</div>
            </div>
          )}
        </div>

        {/* Options */}
        <div style={{ display: 'flex', gap: 16, marginBottom: 16, fontSize: 12 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', color: 'var(--text-secondary)' }}>
            <input type="checkbox" checked={embedMeta} onChange={(e) => setEmbedMeta(e.target.checked)} />
            <Sparkles size={12} /> Embed metadata
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', color: 'var(--text-secondary)' }}>
            <input type="checkbox" checked={embedThumb} onChange={(e) => setEmbedThumb(e.target.checked)} />
            <Film size={12} /> Embed thumbnail
          </label>
        </div>

        {/* Download Button */}
        <button
          className="btn btn-primary"
          disabled={!selectedFormat && tab !== 'combined'}
          onClick={() => onDownload(selectedFormat, tab === 'audio' ? 'audio' : 'best')}
          style={{ width: '100%', padding: '12px 0', fontSize: 14, fontWeight: 600 }}
        >
          <Download size={16} style={{ marginRight: 6 }} />
          Download {tab === 'audio' ? 'Audio' : 'Video'}
        </button>
      </div>
    </div>
  );
}
