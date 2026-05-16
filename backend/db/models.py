"""
DEEP DOWNLOADR — Database Models
SQLAlchemy ORM models for all download tracking, torrent state,
Telegram sessions, settings, and history.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)

# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class DownloadStatus(str, enum.Enum):
    QUEUED = "queued"
    ANALYZING = "analyzing"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    MUXING = "muxing"
    EMBEDDING_METADATA = "embedding_metadata"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DownloadSource(str, enum.Enum):
    DIRECT = "direct"
    YTDLP = "ytdlp"
    HLS = "hls"
    TORRENT = "torrent"
    TELEGRAM = "telegram"
    PLAYLIST = "playlist"


class TorrentState(str, enum.Enum):
    CHECKING = "checking"
    DOWNLOADING = "downloading"
    SEEDING = "seeding"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class MediaType(str, enum.Enum):
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    IMAGE = "image"
    GIF = "gif"
    SUBTITLE = "subtitle"
    OTHER = "other"


# ──────────────────────────────────────────────
# Base
# ──────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ──────────────────────────────────────────────
# Downloads
# ──────────────────────────────────────────────

class Download(Base):
    """Core download record — tracks every download across all sources."""
    __tablename__ = "downloads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    download_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    
    # Source info
    source: Mapped[DownloadSource] = mapped_column(Enum(DownloadSource), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)  # e.g. YouTube video ID
    
    # File info
    title: Mapped[str] = mapped_column(String(512), nullable=False, default="Untitled")
    filename: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    output_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # bytes
    downloaded_size: Mapped[int] = mapped_column(Integer, default=0)
    mime_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    
    # Format selection
    format_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    quality: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # e.g. "1080p"
    codec: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    container: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # mp4, mkv, etc.
    
    # Status
    status: Mapped[DownloadStatus] = mapped_column(
        Enum(DownloadStatus), nullable=False, default=DownloadStatus.QUEUED
    )
    progress: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0 - 100.0
    speed: Mapped[float] = mapped_column(Float, default=0.0)  # bytes/sec
    eta: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # seconds
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Queue management
    priority: Mapped[int] = mapped_column(Integer, default=0)  # higher = higher priority
    queue_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Metadata
    thumbnail_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    uploader: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    upload_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # seconds
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Dedup
    content_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Indexes
    __table_args__ = (
        Index("idx_download_status", "status"),
        Index("idx_download_source", "source"),
        Index("idx_download_created", "created_at"),
    )


# ──────────────────────────────────────────────
# Torrent
# ──────────────────────────────────────────────

class Torrent(Base):
    """Torrent download state tracking."""
    __tablename__ = "torrents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    info_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    magnet_uri: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    torrent_file_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    save_path: Mapped[str] = mapped_column(Text, nullable=False)
    
    # State
    state: Mapped[TorrentState] = mapped_column(
        Enum(TorrentState), nullable=False, default=TorrentState.CHECKING
    )
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    total_size: Mapped[int] = mapped_column(Integer, default=0)
    downloaded: Mapped[int] = mapped_column(Integer, default=0)
    uploaded: Mapped[int] = mapped_column(Integer, default=0)
    download_speed: Mapped[float] = mapped_column(Float, default=0.0)
    upload_speed: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Peers
    seeds: Mapped[int] = mapped_column(Integer, default=0)
    peers: Mapped[int] = mapped_column(Integer, default=0)
    
    # Settings
    sequential: Mapped[bool] = mapped_column(Boolean, default=False)
    upload_limit: Mapped[int] = mapped_column(Integer, default=0)  # 0 = unlimited
    download_limit: Mapped[int] = mapped_column(Integer, default=0)
    
    # File selection (JSON array of selected file indices)
    selected_files: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    file_priorities: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Trackers (JSON array)
    trackers: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    added_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


# ──────────────────────────────────────────────
# Telegram
# ──────────────────────────────────────────────

class TelegramSession(Base):
    """Telegram session and credentials (encrypted)."""
    __tablename__ = "telegram_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    api_id: Mapped[str] = mapped_column(String(32), nullable=False)  # encrypted
    api_hash: Mapped[str] = mapped_column(String(128), nullable=False)  # encrypted
    session_file: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class TelegramDownload(Base):
    """Tracks individual Telegram media downloads for resume support."""
    __tablename__ = "telegram_downloads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    download_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("downloads.download_id"), nullable=False
    )
    
    chat_id: Mapped[int] = mapped_column(Integer, nullable=False)
    message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    file_unique_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    file_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    
    # Resume state
    bytes_written: Mapped[int] = mapped_column(Integer, default=0)
    expected_size: Mapped[int] = mapped_column(Integer, default=0)
    sha256_partial: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    sidecar_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_tg_chat_message", "chat_id", "message_id"),
        Index("idx_tg_file_unique", "file_unique_id"),
    )


# ──────────────────────────────────────────────
# Playlists
# ──────────────────────────────────────────────

class Playlist(Base):
    """Tracked playlists/channels for auto-sync."""
    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    playlist_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)  # youtube, rss, iptv, etc.
    
    # Auto-sync settings
    auto_sync: Mapped[bool] = mapped_column(Boolean, default=False)
    sync_interval_hours: Mapped[int] = mapped_column(Integer, default=6)
    last_synced: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Output settings
    output_folder: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    filename_template: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    default_quality: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    
    # Stats
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    downloaded_items: Mapped[int] = mapped_column(Integer, default=0)
    
    thumbnail_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class PlaylistItem(Base):
    """Individual items within a playlist."""
    __tablename__ = "playlist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    playlist_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("playlists.playlist_id"), nullable=False
    )
    
    item_id: Mapped[str] = mapped_column(String(256), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    index: Mapped[int] = mapped_column(Integer, default=0)  # position in playlist
    
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    is_downloaded: Mapped[bool] = mapped_column(Boolean, default=False)
    download_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    __table_args__ = (
        Index("idx_playlist_item", "playlist_id", "item_id"),
    )


# ──────────────────────────────────────────────
# File Index (for dedup and resume)
# ──────────────────────────────────────────────

class FileIndex(Base):
    """Index of all downloaded/detected files for dedup."""
    __tablename__ = "file_index"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256_sampled: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    
    source: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    download_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    modified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


# ──────────────────────────────────────────────
# Settings
# ──────────────────────────────────────────────

class Setting(Base):
    """Key-value settings storage."""
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value_type: Mapped[str] = mapped_column(String(16), default="string")  # string, int, float, bool, json
    category: Mapped[str] = mapped_column(String(64), default="general")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


# ──────────────────────────────────────────────
# Scheduled Jobs
# ──────────────────────────────────────────────

class ScheduledJob(Base):
    """Scheduled download/sync jobs."""
    __tablename__ = "scheduled_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)  # download, sync, scan
    
    # Schedule
    cron_expression: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    repeat: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Job data (JSON)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_run: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


# ──────────────────────────────────────────────
# Database Setup
# ──────────────────────────────────────────────

import os

DB_DIR = os.path.expanduser("~/.deep-downloadr")
DB_PATH = os.path.join(DB_DIR, "deep_downloadr.db")
DB_URL = f"sqlite:///{DB_PATH}"


def get_engine(db_url: str = DB_URL):
    """Create SQLAlchemy engine."""
    os.makedirs(os.path.dirname(db_url.replace("sqlite:///", "")), exist_ok=True)
    return create_engine(db_url, echo=False, pool_pre_ping=True)


def init_db(db_url: str = DB_URL) -> sessionmaker:
    """Initialize database and create all tables."""
    engine = get_engine(db_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def get_session(db_url: str = DB_URL) -> Session:
    """Get a new database session."""
    SessionLocal = init_db(db_url)
    return SessionLocal()
