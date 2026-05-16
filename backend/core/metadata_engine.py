"""
DEEP DOWNLOADR — Metadata Engine
Fetch metadata via yt-dlp, embed tags via FFmpeg/mutagen,
handle thumbnail resolution hierarchy for all platforms.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Optional

import aiohttp

logger = logging.getLogger("deep-downloadr.metadata")


# ── Thumbnail Resolution Hierarchy ──

THUMBNAIL_HIERARCHY = {
    "youtube": [
        "https://img.youtube.com/vi/{id}/maxresdefault.jpg",
        "https://img.youtube.com/vi/{id}/sddefault.jpg",
        "https://img.youtube.com/vi/{id}/hqdefault.jpg",
        "https://img.youtube.com/vi/{id}/mqdefault.jpg",
    ],
}


async def fetch_best_thumbnail(
    metadata: dict[str, Any],
    output_dir: str,
) -> str | None:
    """Download the highest-resolution thumbnail available."""
    thumbnails = metadata.get("thumbnails", [])
    if not thumbnails:
        thumb_url = metadata.get("thumbnail", "")
        if thumb_url:
            thumbnails = [{"url": thumb_url}]

    # Sort by width descending
    sorted_thumbs = sorted(
        thumbnails,
        key=lambda t: t.get("width", 0) or 0,
        reverse=True,
    )

    os.makedirs(output_dir, exist_ok=True)

    async with aiohttp.ClientSession() as session:
        for thumb in sorted_thumbs:
            url = thumb.get("url", "")
            if not url:
                continue
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        ext = "jpg"
                        ct = resp.headers.get("content-type", "")
                        if "png" in ct:
                            ext = "png"
                        elif "webp" in ct:
                            ext = "webp"

                        thumb_path = os.path.join(output_dir, f"thumbnail.{ext}")
                        with open(thumb_path, "wb") as f:
                            f.write(await resp.read())
                        logger.info(f"Thumbnail saved: {thumb_path}")
                        return thumb_path
            except Exception as e:
                logger.debug(f"Thumbnail fetch failed for {url}: {e}")
                continue

    return None


def build_metadata_tags(metadata: dict[str, Any]) -> dict[str, str]:
    """Build FFmpeg/mutagen metadata tag dict from yt-dlp metadata."""
    tags: dict[str, str] = {}

    mapping = {
        "title": ["title"],
        "artist": ["uploader", "channel", "artist"],
        "album_artist": ["uploader", "channel"],
        "date": ["upload_date"],
        "comment": ["description"],
        "description": ["description"],
        "genre": ["tags", "categories"],
        "synopsis": ["description"],
    }

    for tag, keys in mapping.items():
        for key in keys:
            val = metadata.get(key)
            if val:
                if isinstance(val, list):
                    tags[tag] = ", ".join(str(v) for v in val[:5])
                else:
                    tags[tag] = str(val)[:1000]
                break

    # Playlist info
    if metadata.get("playlist_index"):
        tags["track"] = str(metadata["playlist_index"])
    if metadata.get("playlist_title"):
        tags["album"] = metadata["playlist_title"]

    return tags


async def embed_metadata_into_file(
    file_path: str,
    metadata: dict[str, Any],
    thumbnail_path: str | None = None,
) -> bool:
    """
    Embed metadata tags and thumbnail into a media file.
    Uses mutagen for audio files, FFmpeg for video files.
    """
    ext = Path(file_path).suffix.lower()
    tags = build_metadata_tags(metadata)

    if ext in (".mp3", ".m4a", ".flac", ".ogg", ".opus"):
        return _embed_audio_tags(file_path, tags, thumbnail_path)
    elif ext in (".mp4", ".mkv", ".webm"):
        return await _embed_video_tags(file_path, tags, thumbnail_path)

    return False


def _embed_audio_tags(
    file_path: str,
    tags: dict[str, str],
    thumbnail_path: str | None = None,
) -> bool:
    """Embed ID3/Vorbis tags into audio files using mutagen."""
    try:
        from mutagen import File
        from mutagen.id3 import APIC, ID3
        from mutagen.mp4 import MP4, MP4Cover

        audio = File(file_path, easy=True)
        if audio is None:
            return False

        for key, value in tags.items():
            try:
                audio[key] = value
            except Exception:
                pass

        audio.save()

        # Embed thumbnail as cover art
        if thumbnail_path and os.path.exists(thumbnail_path):
            ext = Path(file_path).suffix.lower()
            with open(thumbnail_path, "rb") as f:
                thumb_data = f.read()

            if ext == ".mp3":
                audio_raw = ID3(file_path)
                audio_raw.add(APIC(
                    encoding=3,
                    mime="image/jpeg",
                    type=3,
                    desc="Cover",
                    data=thumb_data,
                ))
                audio_raw.save()
            elif ext == ".m4a":
                mp4 = MP4(file_path)
                mp4["covr"] = [MP4Cover(thumb_data, imageformat=MP4Cover.FORMAT_JPEG)]
                mp4.save()

        logger.info(f"Audio metadata embedded: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Audio metadata embedding failed: {e}")
        return False


async def _embed_video_tags(
    file_path: str,
    tags: dict[str, str],
    thumbnail_path: str | None = None,
) -> bool:
    """Embed metadata into video files using FFmpeg."""
    try:
        from backend.utils.ffmpeg_utils import embed_metadata
        await embed_metadata(file_path, tags, thumbnail_path)
        return True
    except Exception as e:
        logger.error(f"Video metadata embedding failed: {e}")
        return False
