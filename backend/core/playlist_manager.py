"""
DEEP DOWNLOADR — Playlist Manager
YouTube playlists, RSS/Atom feeds, Instagram profiles,
IPTV playlists, and auto-sync with configurable polling.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("deep-downloadr.playlist")


async def fetch_youtube_playlist(url: str) -> dict[str, Any]:
    """Fetch YouTube playlist metadata via yt-dlp --flat-playlist."""
    import shutil
    ytdlp = shutil.which("yt-dlp") or "yt-dlp"

    cmd = [ytdlp, "--dump-json", "--flat-playlist", "--no-warnings", url]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    items = []
    for line in stdout.decode("utf-8").strip().split("\n"):
        if not line:
            continue
        try:
            data = json.loads(line)
            items.append({
                "item_id": data.get("id", ""),
                "title": data.get("title", "Untitled"),
                "url": data.get("url", data.get("webpage_url", "")),
                "duration": data.get("duration"),
                "thumbnail_url": data.get("thumbnails", [{}])[-1].get("url") if data.get("thumbnails") else None,
                "uploader": data.get("uploader", ""),
            })
        except json.JSONDecodeError:
            continue

    # Get playlist metadata from first entry or separate call
    playlist_name = items[0].get("uploader", "Playlist") if items else "Unknown Playlist"

    return {
        "name": playlist_name,
        "items": items,
        "total": len(items),
        "source_type": "youtube",
    }


async def fetch_rss_feed(url: str) -> dict[str, Any]:
    """Parse RSS/Atom feed for podcast episodes."""
    import feedparser
    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            content = await resp.text()

    feed = feedparser.parse(content)
    items = []

    for i, entry in enumerate(feed.entries):
        media_url = ""
        # Look for enclosures (podcast audio/video)
        if entry.get("enclosures"):
            media_url = entry.enclosures[0].get("href", "")
        elif entry.get("links"):
            for link in entry.links:
                if link.get("type", "").startswith(("audio/", "video/")):
                    media_url = link.get("href", "")
                    break

        if not media_url:
            media_url = entry.get("link", "")

        items.append({
            "item_id": entry.get("id", str(i)),
            "title": entry.get("title", "Untitled"),
            "url": media_url,
            "duration": None,
            "thumbnail_url": entry.get("image", {}).get("href") if hasattr(entry, "image") else None,
        })

    return {
        "name": feed.feed.get("title", "RSS Feed"),
        "items": items,
        "total": len(items),
        "source_type": "rss",
    }


async def fetch_m3u_playlist(file_path: str) -> dict[str, Any]:
    """Parse M3U/IPTV playlist file."""
    items = []
    current_title = ""

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#EXTINF:"):
                # Parse title from #EXTINF line
                parts = line.split(",", 1)
                current_title = parts[1].strip() if len(parts) > 1 else ""
            elif line and not line.startswith("#"):
                items.append({
                    "item_id": str(len(items)),
                    "title": current_title or f"Stream {len(items) + 1}",
                    "url": line,
                    "duration": None,
                    "thumbnail_url": None,
                })
                current_title = ""

    return {
        "name": os.path.splitext(os.path.basename(file_path))[0],
        "items": items,
        "total": len(items),
        "source_type": "iptv",
    }


async def fetch_playlist(url: str) -> dict[str, Any]:
    """Auto-detect playlist type and fetch metadata."""
    if url.endswith((".m3u", ".m3u8")) and os.path.exists(url):
        return await fetch_m3u_playlist(url)
    elif "youtube.com" in url or "youtu.be" in url:
        return await fetch_youtube_playlist(url)
    elif url.startswith(("http://", "https://")) and any(url.endswith(ext) for ext in (".rss", ".xml", ".atom")):
        return await fetch_rss_feed(url)
    else:
        # Try yt-dlp for generic URL
        return await fetch_youtube_playlist(url)
