"""
DEEP DOWNLOADR — Torrent Engine
libtorrent session manager with DHT, PEX, LSD,
sequential download, file selection, and stats tracking.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("deep-downloadr.torrent")

# ──────────────────────────────────────────────
# Torrent Session Manager
# ──────────────────────────────────────────────

class TorrentEngine:
    """Manages the libtorrent session and all torrent operations."""

    def __init__(self, save_path: str | None = None):
        self.save_path = save_path or os.path.expanduser("~/Downloads/DEEP DOWNLOADR/Torrents")
        self.session = None
        self.handles: dict[str, Any] = {}  # info_hash -> handle
        self._running = False

    def start(self) -> None:
        """Initialize libtorrent session."""
        try:
            import libtorrent as lt
        except ImportError:
            logger.error("python-libtorrent not installed. Install via: apt install python3-libtorrent")
            return

        settings = {
            "user_agent": "DEEP_DOWNLOADR/1.0",
            "listen_interfaces": "0.0.0.0:6881,[::]:6881",
            "enable_dht": True,
            "enable_lsd": True,
            "enable_upnp": True,
            "enable_natpmp": True,
            "announce_to_all_tiers": True,
            "announce_to_all_trackers": True,
            "max_connections_per_torrent": 200,
            "active_downloads": 5,
            "active_seeds": 10,
        }

        self.session = lt.session(settings)
        self.session.add_dht_router("router.bittorrent.com", 6881)
        self.session.add_dht_router("router.utorrent.com", 6881)
        self.session.add_dht_router("dht.transmissionbt.com", 6881)
        self.session.start_dht()

        self._running = True
        logger.info("Torrent engine started")

    def stop(self) -> None:
        """Shutdown torrent session."""
        self._running = False
        if self.session:
            for h in self.handles.values():
                self.session.remove_torrent(h)
            self.handles.clear()
            logger.info("Torrent engine stopped")

    def add_magnet(
        self,
        magnet_uri: str,
        save_path: str | None = None,
        sequential: bool = False,
    ) -> dict[str, Any]:
        """Add a torrent from a magnet URI."""
        import libtorrent as lt

        if not self.session:
            self.start()

        params = lt.parse_magnet_uri(magnet_uri)
        params.save_path = save_path or self.save_path
        os.makedirs(params.save_path, exist_ok=True)

        handle = self.session.add_torrent(params)

        if sequential:
            handle.set_sequential_download(True)

        info_hash = str(handle.info_hash())
        self.handles[info_hash] = handle

        logger.info(f"Added magnet: {info_hash}")
        return {"info_hash": info_hash, "name": handle.name() or "Fetching metadata..."}

    def add_torrent_file(
        self,
        torrent_path: str,
        save_path: str | None = None,
        sequential: bool = False,
        selected_files: list[int] | None = None,
    ) -> dict[str, Any]:
        """Add a torrent from a .torrent file."""
        import libtorrent as lt

        if not self.session:
            self.start()

        info = lt.torrent_info(torrent_path)
        params = lt.add_torrent_params()
        params.ti = info
        params.save_path = save_path or self.save_path
        os.makedirs(params.save_path, exist_ok=True)

        handle = self.session.add_torrent(params)

        if sequential:
            handle.set_sequential_download(True)

        # File selection
        if selected_files is not None:
            priorities = [0] * info.num_files()
            for idx in selected_files:
                if 0 <= idx < info.num_files():
                    priorities[idx] = 4  # Normal priority
            handle.prioritize_files(priorities)

        info_hash = str(handle.info_hash())
        self.handles[info_hash] = handle

        logger.info(f"Added torrent file: {info.name()}")
        return {"info_hash": info_hash, "name": info.name()}

    def get_file_list(self, info_hash: str) -> list[dict[str, Any]]:
        """Get the file tree for a torrent."""
        import libtorrent as lt

        handle = self.handles.get(info_hash)
        if not handle:
            return []

        info = handle.torrent_file()
        if not info:
            return []  # Metadata not yet available

        files = []
        file_storage = info.files()
        file_progress = handle.file_progress()

        for i in range(file_storage.num_files()):
            files.append({
                "index": i,
                "path": file_storage.file_path(i),
                "name": file_storage.file_name(i),
                "size": file_storage.file_size(i),
                "progress": file_progress[i] / max(file_storage.file_size(i), 1) if file_progress else 0,
                "priority": handle.file_priorities()[i],
            })

        return files

    def set_file_priorities(self, info_hash: str, priorities: dict[int, int]) -> None:
        """Set priority for individual files. 0=skip, 1=low, 4=normal, 7=high."""
        handle = self.handles.get(info_hash)
        if not handle:
            return

        current = list(handle.file_priorities())
        for idx, priority in priorities.items():
            if 0 <= idx < len(current):
                current[idx] = priority
        handle.prioritize_files(current)

    def get_status(self, info_hash: str) -> dict[str, Any]:
        """Get detailed status for a torrent."""
        import libtorrent as lt

        handle = self.handles.get(info_hash)
        if not handle:
            return {}

        s = handle.status()
        state_map = {
            lt.torrent_status.checking_files: "checking",
            lt.torrent_status.downloading_metadata: "checking",
            lt.torrent_status.downloading: "downloading",
            lt.torrent_status.finished: "seeding",
            lt.torrent_status.seeding: "seeding",
            lt.torrent_status.checking_resume_data: "checking",
        }

        return {
            "info_hash": info_hash,
            "name": s.name,
            "state": state_map.get(s.state, "unknown"),
            "progress": s.progress,
            "download_speed": s.download_rate,
            "upload_speed": s.upload_rate,
            "total_size": s.total_wanted,
            "downloaded": s.total_wanted_done,
            "uploaded": s.all_time_upload,
            "seeds": s.num_seeds,
            "peers": s.num_peers,
            "eta": int((s.total_wanted - s.total_wanted_done) / max(s.download_rate, 1)) if s.download_rate > 0 else None,
            "pieces": {
                "total": s.num_pieces,
                "have": s.num_pieces - s.num_pieces,  # Simplified
            },
        }

    def get_all_status(self) -> list[dict[str, Any]]:
        """Get status for all torrents."""
        return [self.get_status(ih) for ih in self.handles]

    def pause(self, info_hash: str) -> None:
        handle = self.handles.get(info_hash)
        if handle:
            handle.pause()

    def resume(self, info_hash: str) -> None:
        handle = self.handles.get(info_hash)
        if handle:
            handle.resume()

    def remove(self, info_hash: str, delete_files: bool = False) -> None:
        import libtorrent as lt
        handle = self.handles.pop(info_hash, None)
        if handle and self.session:
            options = lt.options_t.delete_files if delete_files else 0
            self.session.remove_torrent(handle, options)

    def add_trackers(self, info_hash: str, trackers: list[str]) -> None:
        handle = self.handles.get(info_hash)
        if handle:
            for url in trackers:
                handle.add_tracker({"url": url, "tier": 0})


# Global engine instance
_engine: TorrentEngine | None = None

def get_engine() -> TorrentEngine:
    global _engine
    if _engine is None:
        _engine = TorrentEngine()
    return _engine


# ── API Functions (called from FastAPI) ──

async def add_torrent(
    uri: str,
    save_path: str | None = None,
    selected_files: list[int] | None = None,
    sequential: bool = False,
) -> dict[str, Any]:
    """Add a torrent from magnet or file path."""
    engine = get_engine()
    if uri.startswith("magnet:"):
        return engine.add_magnet(uri, save_path, sequential)
    elif uri.endswith(".torrent") and os.path.exists(uri):
        return engine.add_torrent_file(uri, save_path, sequential, selected_files)
    else:
        raise ValueError(f"Invalid torrent URI: {uri}")
