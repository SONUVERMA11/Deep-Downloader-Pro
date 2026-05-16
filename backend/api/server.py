"""
DEEP DOWNLOADR — FastAPI Backend Server
Local API server running on 127.0.0.1:18920
Handles all download management, torrent ops, Telegram integration,
and settings via REST + WebSocket for real-time progress.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.db.models import (
    DB_URL,
    Download,
    DownloadSource,
    DownloadStatus,
    Setting,
    Torrent,
    TorrentState,
    get_session,
    init_db,
)

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────

LOG_DIR = os.path.expanduser("~/.deep-downloadr/logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "server.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("deep-downloadr")

# ──────────────────────────────────────────────
# WebSocket Connection Manager
# ──────────────────────────────────────────────

class ConnectionManager:
    """Manages WebSocket connections for real-time progress updates."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Active: {len(self.active_connections)}")

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Send a message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.active_connections.remove(conn)

    async def send_progress(
        self,
        download_id: str,
        progress: float,
        speed: float,
        eta: int | None,
        status: str,
        downloaded: int = 0,
        total: int = 0,
    ) -> None:
        """Broadcast download progress update."""
        await self.broadcast(
            {
                "type": "progress",
                "download_id": download_id,
                "progress": progress,
                "speed": speed,
                "eta": eta,
                "status": status,
                "downloaded": downloaded,
                "total": total,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )


manager = ConnectionManager()

# ──────────────────────────────────────────────
# Active Downloads Tracker
# ──────────────────────────────────────────────

active_downloads: dict[str, dict[str, Any]] = {}

# ──────────────────────────────────────────────
# Pydantic Models (API Request/Response)
# ──────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    url: str


class AnalyzeResponse(BaseModel):
    success: bool
    title: str = ""
    thumbnail: str = ""
    duration: int | None = None
    uploader: str = ""
    formats: list[dict[str, Any]] = []
    subtitles: dict[str, Any] = {}
    metadata: dict[str, Any] = {}


class DownloadRequest(BaseModel):
    url: str
    format_id: Optional[str] = None
    output_path: Optional[str] = None
    quality: Optional[str] = None
    filename_template: Optional[str] = None
    embed_metadata: bool = True
    embed_thumbnail: bool = True


class DownloadResponse(BaseModel):
    success: bool
    download_id: str
    message: str


class PauseResumeRequest(BaseModel):
    download_id: str


class TorrentSearchRequest(BaseModel):
    query: str
    category: Optional[str] = None
    min_seeds: int = 0


class TorrentAddRequest(BaseModel):
    uri: str  # magnet link or .torrent path
    save_path: Optional[str] = None
    selected_files: Optional[list[int]] = None
    sequential: bool = False


class SettingsUpdate(BaseModel):
    settings: dict[str, Any]


# ──────────────────────────────────────────────
# App Lifecycle
# ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """App startup and shutdown."""
    logger.info("🚀 DEEP DOWNLOADR Backend starting...")
    
    # Initialize database
    init_db()
    logger.info("✅ Database initialized")
    
    # Initialize default settings
    _init_default_settings()
    logger.info("✅ Default settings loaded")
    
    yield
    
    logger.info("🛑 DEEP DOWNLOADR Backend shutting down...")


def _init_default_settings() -> None:
    """Initialize default settings if they don't exist."""
    defaults = {
        "download.save_path": os.path.expanduser("~/Downloads/DEEP DOWNLOADR"),
        "download.concurrent": "3",
        "download.retry_attempts": "3",
        "download.filename_template": "{title}.{ext}",
        "speed.bandwidth_limit": "0",
        "speed.connections_per_download": "16",
        "format.default_quality": "best",
        "format.default_container": "mp4",
        "format.subtitle_language": "en",
        "torrent.listen_port_start": "6881",
        "torrent.listen_port_end": "6889",
        "torrent.max_upload_speed": "0",
        "torrent.max_connections": "200",
        "torrent.seed_ratio_limit": "2.0",
        "torrent.dht_enabled": "true",
        "torrent.pex_enabled": "true",
        "theme.current": "dark-contrast",
        "theme.font_size": "14",
        "general.launch_at_login": "false",
        "general.minimize_to_tray": "true",
        "advanced.debug_log": "false",
    }
    
    session = get_session()
    try:
        for key, value in defaults.items():
            existing = session.query(Setting).filter_by(key=key).first()
            if not existing:
                category = key.split(".")[0]
                setting = Setting(key=key, value=value, category=category)
                session.add(setting)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to init settings: {e}")
    finally:
        session.close()


# ──────────────────────────────────────────────
# FastAPI App
# ──────────────────────────────────────────────

app = FastAPI(
    title="DEEP DOWNLOADR API",
    version="1.0.0",
    description="Local API for DEEP DOWNLOADR media downloader",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# Health Check
# ──────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """Backend health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "active_downloads": len(active_downloads),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ──────────────────────────────────────────────
# URL Analysis
# ──────────────────────────────────────────────

@app.post("/api/analyze")
async def analyze_url(request: AnalyzeRequest):
    """
    Analyze a URL using yt-dlp and return available formats, metadata, thumbnails.
    """
    try:
        # Import here to avoid circular imports and allow lazy loading
        from backend.core.downloader import analyze_url as _analyze

        result = await _analyze(request.url)
        return {"success": True, **result}
    except ImportError:
        # Stub response when downloader module not yet implemented
        return {
            "success": True,
            "title": "Sample Video",
            "thumbnail": "",
            "duration": 0,
            "uploader": "Unknown",
            "formats": [],
            "subtitles": {},
            "metadata": {"url": request.url},
            "message": "Downloader engine not yet initialized",
        }
    except Exception as e:
        logger.error(f"URL analysis failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ──────────────────────────────────────────────
# Download Management
# ──────────────────────────────────────────────

@app.post("/api/download")
async def start_download(request: DownloadRequest):
    """Start a new download with the selected format/options."""
    download_id = f"dl_{uuid.uuid4().hex[:12]}"
    
    session = get_session()
    try:
        download = Download(
            download_id=download_id,
            source=DownloadSource.YTDLP,
            source_url=request.url,
            title=request.url.split("/")[-1] or "Untitled",
            format_id=request.format_id,
            quality=request.quality,
            output_path=request.output_path or os.path.expanduser("~/Downloads/DEEP DOWNLOADR"),
            status=DownloadStatus.QUEUED,
        )
        session.add(download)
        session.commit()
        
        # Track active download
        active_downloads[download_id] = {
            "id": download_id,
            "url": request.url,
            "status": "queued",
            "progress": 0,
            "speed": 0,
            "title": download.title,
        }
        
        # Broadcast new download event
        await manager.broadcast({
            "type": "download_added",
            "download_id": download_id,
            "url": request.url,
            "status": "queued",
        })
        
        # TODO: Actually start the download via downloader engine
        # asyncio.create_task(_run_download(download_id, request))
        
        return {
            "success": True,
            "download_id": download_id,
            "message": "Download queued",
        }
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to start download: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.post("/api/pause")
async def pause_download(request: PauseResumeRequest):
    """Pause an active download."""
    download_id = request.download_id
    
    if download_id in active_downloads:
        active_downloads[download_id]["status"] = "paused"
        
        session = get_session()
        try:
            dl = session.query(Download).filter_by(download_id=download_id).first()
            if dl:
                dl.status = DownloadStatus.PAUSED
                session.commit()
        finally:
            session.close()
        
        await manager.broadcast({
            "type": "status_change",
            "download_id": download_id,
            "status": "paused",
        })
        
        return {"success": True, "message": "Download paused"}
    
    raise HTTPException(status_code=404, detail="Download not found")


@app.post("/api/resume")
async def resume_download(request: PauseResumeRequest):
    """Resume a paused download."""
    download_id = request.download_id
    
    if download_id in active_downloads:
        active_downloads[download_id]["status"] = "downloading"
        
        session = get_session()
        try:
            dl = session.query(Download).filter_by(download_id=download_id).first()
            if dl:
                dl.status = DownloadStatus.DOWNLOADING
                session.commit()
        finally:
            session.close()
        
        await manager.broadcast({
            "type": "status_change",
            "download_id": download_id,
            "status": "downloading",
        })
        
        return {"success": True, "message": "Download resumed"}
    
    raise HTTPException(status_code=404, detail="Download not found")


@app.post("/api/cancel")
async def cancel_download(request: PauseResumeRequest):
    """Cancel a download."""
    download_id = request.download_id
    
    if download_id in active_downloads:
        del active_downloads[download_id]
        
        session = get_session()
        try:
            dl = session.query(Download).filter_by(download_id=download_id).first()
            if dl:
                dl.status = DownloadStatus.CANCELLED
                session.commit()
        finally:
            session.close()
        
        await manager.broadcast({
            "type": "status_change",
            "download_id": download_id,
            "status": "cancelled",
        })
        
        return {"success": True, "message": "Download cancelled"}
    
    raise HTTPException(status_code=404, detail="Download not found")


@app.get("/api/downloads")
async def get_downloads():
    """Get all active and queued downloads."""
    session = get_session()
    try:
        downloads = (
            session.query(Download)
            .filter(
                Download.status.in_([
                    DownloadStatus.DOWNLOADING,
                    DownloadStatus.QUEUED,
                    DownloadStatus.PAUSED,
                    DownloadStatus.ANALYZING,
                    DownloadStatus.MUXING,
                ])
            )
            .order_by(Download.queue_position, Download.created_at)
            .all()
        )
        
        result = []
        for dl in downloads:
            # Merge with live state if available
            live = active_downloads.get(dl.download_id, {})
            result.append({
                "download_id": dl.download_id,
                "title": dl.title,
                "url": dl.source_url,
                "status": live.get("status", dl.status.value),
                "progress": live.get("progress", dl.progress),
                "speed": live.get("speed", dl.speed),
                "eta": dl.eta,
                "file_size": dl.file_size,
                "downloaded_size": dl.downloaded_size,
                "source": dl.source.value,
                "quality": dl.quality,
                "thumbnail_url": dl.thumbnail_url,
                "uploader": dl.uploader,
                "created_at": dl.created_at.isoformat() if dl.created_at else None,
            })
        
        return {"success": True, "downloads": result}
    finally:
        session.close()


@app.get("/api/history")
async def get_history():
    """Get download history (completed, failed, cancelled)."""
    session = get_session()
    try:
        downloads = (
            session.query(Download)
            .filter(
                Download.status.in_([
                    DownloadStatus.COMPLETED,
                    DownloadStatus.FAILED,
                    DownloadStatus.CANCELLED,
                ])
            )
            .order_by(Download.completed_at.desc())
            .limit(200)
            .all()
        )
        
        result = []
        for dl in downloads:
            result.append({
                "download_id": dl.download_id,
                "title": dl.title,
                "url": dl.source_url,
                "status": dl.status.value,
                "file_size": dl.file_size,
                "source": dl.source.value,
                "quality": dl.quality,
                "output_path": dl.output_path,
                "filename": dl.filename,
                "thumbnail_url": dl.thumbnail_url,
                "uploader": dl.uploader,
                "duration": dl.duration,
                "completed_at": dl.completed_at.isoformat() if dl.completed_at else None,
                "created_at": dl.created_at.isoformat() if dl.created_at else None,
                "error_message": dl.error_message,
            })
        
        return {"success": True, "history": result}
    finally:
        session.close()


# ──────────────────────────────────────────────
# Torrent
# ──────────────────────────────────────────────

@app.post("/api/torrent/search")
async def search_torrents(request: TorrentSearchRequest):
    """Search torrents across multiple indexes."""
    try:
        from backend.core.torrent_search import search as _search

        results = await _search(request.query, request.category, request.min_seeds)
        return {"success": True, "results": results}
    except ImportError:
        return {
            "success": True,
            "results": [],
            "message": "Torrent search engine not yet initialized",
        }
    except Exception as e:
        logger.error(f"Torrent search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/torrent/add")
async def add_torrent(request: TorrentAddRequest):
    """Add a torrent (magnet link or .torrent file)."""
    try:
        from backend.core.torrent_engine import add_torrent as _add

        result = await _add(
            request.uri,
            request.save_path,
            request.selected_files,
            request.sequential,
        )
        return {"success": True, **result}
    except ImportError:
        return {
            "success": True,
            "message": "Torrent engine not yet initialized",
            "info_hash": "stub",
        }
    except Exception as e:
        logger.error(f"Failed to add torrent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/torrents")
async def get_torrents():
    """Get all tracked torrents."""
    session = get_session()
    try:
        torrents = session.query(Torrent).order_by(Torrent.added_at.desc()).all()
        result = []
        for t in torrents:
            result.append({
                "info_hash": t.info_hash,
                "name": t.name,
                "state": t.state.value,
                "progress": t.progress,
                "total_size": t.total_size,
                "downloaded": t.downloaded,
                "uploaded": t.uploaded,
                "download_speed": t.download_speed,
                "upload_speed": t.upload_speed,
                "seeds": t.seeds,
                "peers": t.peers,
                "added_at": t.added_at.isoformat() if t.added_at else None,
            })
        return {"success": True, "torrents": result}
    finally:
        session.close()


# ──────────────────────────────────────────────
# Settings
# ──────────────────────────────────────────────

@app.get("/api/settings")
async def get_settings():
    """Get all settings."""
    session = get_session()
    try:
        settings = session.query(Setting).all()
        result = {}
        for s in settings:
            result[s.key] = {
                "value": s.value,
                "type": s.value_type,
                "category": s.category,
            }
        return {"success": True, "settings": result}
    finally:
        session.close()


@app.post("/api/settings")
async def update_settings(update: dict[str, Any]):
    """Update settings."""
    session = get_session()
    try:
        for key, value in update.items():
            if key == "settings":
                # Handle nested settings object
                for k, v in value.items():
                    setting = session.query(Setting).filter_by(key=k).first()
                    if setting:
                        setting.value = str(v)
                    else:
                        category = k.split(".")[0]
                        setting = Setting(key=k, value=str(v), category=category)
                        session.add(setting)
            else:
                setting = session.query(Setting).filter_by(key=key).first()
                if setting:
                    setting.value = str(value)
                else:
                    category = key.split(".")[0]
                    setting = Setting(key=key, value=str(value), category=category)
                    session.add(setting)
        session.commit()
        return {"success": True, "message": "Settings updated"}
    except Exception as e:
        session.rollback()
        logger.error(f"Settings update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


# ──────────────────────────────────────────────
# WebSocket — Real-time Progress
# ──────────────────────────────────────────────

@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time progress updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Receive messages from frontend (commands, keep-alive, etc.)
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                msg_type = message.get("type", "")
                
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                elif msg_type == "subscribe":
                    # Client subscribes to specific download updates
                    logger.info(f"Client subscribed to: {message.get('download_id')}")
                    
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ──────────────────────────────────────────────
# Stats
# ──────────────────────────────────────────────

@app.get("/api/stats")
async def get_stats():
    """Get overall application statistics."""
    session = get_session()
    try:
        total_downloads = session.query(Download).count()
        completed = session.query(Download).filter_by(status=DownloadStatus.COMPLETED).count()
        active = session.query(Download).filter(
            Download.status.in_([DownloadStatus.DOWNLOADING, DownloadStatus.QUEUED])
        ).count()
        total_torrents = session.query(Torrent).count()
        
        # Calculate total downloaded bytes today
        from datetime import date
        today = datetime.combine(date.today(), datetime.min.time())
        today_bytes = (
            session.query(Download)
            .filter(
                Download.status == DownloadStatus.COMPLETED,
                Download.completed_at >= today,
            )
            .with_entities(Download.file_size)
            .all()
        )
        total_today = sum(b[0] for b in today_bytes if b[0])
        
        return {
            "success": True,
            "total_downloads": total_downloads,
            "completed": completed,
            "active": active,
            "total_torrents": total_torrents,
            "bytes_today": total_today,
            "active_connections": len(manager.active_connections),
        }
    finally:
        session.close()
