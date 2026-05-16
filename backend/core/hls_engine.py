"""
DEEP DOWNLOADR — HLS/M3U8 Engine
Full pipeline: master playlist parsing, async segment downloading,
AES-128 decryption, live stream recording, and FFmpeg muxing.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
import struct
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

import aiohttp
import m3u8

logger = logging.getLogger("deep-downloadr.hls")

TEMP_DIR = Path.home() / ".deep-downloadr" / "tmp" / "hls"
TEMP_DIR.mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────
# Data Classes
# ──────────────────────────────────────────────

@dataclass
class HLSRendition:
    """Represents a single HLS rendition (quality level)."""
    bandwidth: int
    resolution: str
    codecs: str
    uri: str
    name: str = ""
    frame_rate: float | None = None
    audio_group: str | None = None


@dataclass
class HLSMediaTrack:
    """Audio/subtitle track from HLS playlist."""
    type: str  # "AUDIO" or "SUBTITLES"
    group_id: str
    language: str
    name: str
    uri: str
    default: bool = False
    autoselect: bool = False


@dataclass
class HLSAnalysis:
    """Result of analyzing an HLS stream."""
    master_url: str
    is_live: bool
    video_renditions: list[HLSRendition]
    audio_tracks: list[HLSMediaTrack]
    subtitle_tracks: list[HLSMediaTrack]
    duration: float | None = None


@dataclass
class SegmentTask:
    """A single segment download task."""
    index: int
    url: str
    key_url: str | None = None
    key_iv: bytes | None = None
    duration: float = 0.0
    downloaded: bool = False
    retries: int = 0
    output_path: str = ""


# ──────────────────────────────────────────────
# HLS Analyzer
# ──────────────────────────────────────────────

async def analyze_hls(url: str) -> HLSAnalysis:
    """
    Fetch and parse an HLS master playlist.
    Returns available renditions, audio tracks, and subtitle tracks.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            content = await resp.text()

    playlist = m3u8.loads(content, uri=url)

    video_renditions: list[HLSRendition] = []
    audio_tracks: list[HLSMediaTrack] = []
    subtitle_tracks: list[HLSMediaTrack] = []

    is_live = not playlist.is_endlist if hasattr(playlist, 'is_endlist') else False

    # Check if this is a master playlist or a media playlist
    if playlist.is_variant:
        for p in playlist.playlists:
            res = f"{p.stream_info.resolution[0]}x{p.stream_info.resolution[1]}" if p.stream_info.resolution else "Unknown"
            height = p.stream_info.resolution[1] if p.stream_info.resolution else 0
            
            video_renditions.append(HLSRendition(
                bandwidth=p.stream_info.bandwidth,
                resolution=res,
                codecs=p.stream_info.codecs or "",
                uri=p.absolute_uri,
                name=f"{height}p" if height else f"{p.stream_info.bandwidth // 1000}kbps",
                frame_rate=getattr(p.stream_info, 'frame_rate', None),
                audio_group=getattr(p.stream_info, 'audio', None),
            ))

        # Parse media groups (audio, subtitles)
        for media in playlist.media:
            track = HLSMediaTrack(
                type=media.type,
                group_id=media.group_id or "",
                language=media.language or "und",
                name=media.name or media.language or "Default",
                uri=media.absolute_uri or "",
                default=media.default == "YES",
                autoselect=media.autoselect == "YES",
            )
            if media.type == "AUDIO":
                audio_tracks.append(track)
            elif media.type == "SUBTITLES":
                subtitle_tracks.append(track)

        # Sort renditions by bandwidth (highest first)
        video_renditions.sort(key=lambda r: r.bandwidth, reverse=True)
    else:
        # Single media playlist — treat as single rendition
        is_live = not playlist.is_endlist
        duration = sum(seg.duration for seg in playlist.segments) if playlist.segments else None

        video_renditions.append(HLSRendition(
            bandwidth=0,
            resolution="Unknown",
            codecs="",
            uri=url,
            name="Default",
        ))

    return HLSAnalysis(
        master_url=url,
        is_live=is_live,
        video_renditions=video_renditions,
        audio_tracks=audio_tracks,
        subtitle_tracks=subtitle_tracks,
    )


# ──────────────────────────────────────────────
# AES-128 Decryption
# ──────────────────────────────────────────────

class AESDecryptor:
    """AES-128-CBC decryptor for HLS segments."""

    def __init__(self):
        self._key_cache: dict[str, bytes] = {}

    async def fetch_key(self, key_url: str, session: aiohttp.ClientSession) -> bytes:
        """Fetch and cache AES key."""
        if key_url in self._key_cache:
            return self._key_cache[key_url]

        async with session.get(key_url) as resp:
            key = await resp.read()
            self._key_cache[key_url] = key
            return key

    def decrypt(self, data: bytes, key: bytes, iv: bytes) -> bytes:
        """Decrypt AES-128-CBC encrypted segment."""
        from Crypto.Cipher import AES
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(data)
        # Remove PKCS7 padding
        pad_len = decrypted[-1]
        if pad_len <= 16:
            decrypted = decrypted[:-pad_len]
        return decrypted


# ──────────────────────────────────────────────
# Async Segment Downloader
# ──────────────────────────────────────────────

async def download_hls_stream(
    rendition_url: str,
    output_path: str,
    filename: str,
    max_workers: int = 24,
    max_retries: int = 3,
    progress_callback: Callable | None = None,
    audio_url: str | None = None,
    subtitle_url: str | None = None,
) -> str:
    """
    Download an HLS stream with async segment fetching,
    AES-128 decryption, and FFmpeg muxing.
    """
    # Create temp directory for segments
    job_id = hashlib.md5(rendition_url.encode()).hexdigest()[:12]
    seg_dir = TEMP_DIR / job_id
    seg_dir.mkdir(parents=True, exist_ok=True)

    # Fetch media playlist
    async with aiohttp.ClientSession() as session:
        async with session.get(rendition_url) as resp:
            content = await resp.text()

    playlist = m3u8.loads(content, uri=rendition_url)
    decryptor = AESDecryptor()

    # Build segment tasks
    tasks: list[SegmentTask] = []
    for i, segment in enumerate(playlist.segments):
        key_url = None
        key_iv = None

        if segment.key and segment.key.method == "AES-128":
            key_url = segment.key.absolute_uri
            if segment.key.iv:
                key_iv = bytes.fromhex(segment.key.iv.replace("0x", ""))
            else:
                key_iv = struct.pack(">QQ", 0, i)

        tasks.append(SegmentTask(
            index=i,
            url=segment.absolute_uri,
            key_url=key_url,
            key_iv=key_iv,
            duration=segment.duration,
            output_path=str(seg_dir / f"segment_{i:05d}.ts"),
        ))

    total_segments = len(tasks)
    completed = 0
    semaphore = asyncio.Semaphore(max_workers)

    async def download_segment(task: SegmentTask, session: aiohttp.ClientSession):
        nonlocal completed
        async with semaphore:
            for attempt in range(max_retries):
                try:
                    async with session.get(task.url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        data = await resp.read()

                    # Decrypt if encrypted
                    if task.key_url and task.key_iv:
                        key = await decryptor.fetch_key(task.key_url, session)
                        data = decryptor.decrypt(data, key, task.key_iv)

                    # Write to disk immediately (memory efficient)
                    with open(task.output_path, "wb") as f:
                        f.write(data)

                    task.downloaded = True
                    completed += 1

                    if progress_callback:
                        await progress_callback(completed / total_segments * 100)

                    return
                except Exception as e:
                    task.retries += 1
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1 * (attempt + 1))
                    else:
                        logger.error(f"Segment {task.index} failed after {max_retries} attempts: {e}")
                        raise

    # Download all segments concurrently
    async with aiohttp.ClientSession() as session:
        await asyncio.gather(*[download_segment(t, session) for t in tasks])

    # Mux segments with FFmpeg
    from backend.utils.ffmpeg_utils import concat_ts_segments

    output_file = os.path.join(output_path, filename)
    os.makedirs(output_path, exist_ok=True)

    await concat_ts_segments(str(seg_dir), output_file)

    # Cleanup temp segments
    import shutil
    shutil.rmtree(str(seg_dir), ignore_errors=True)

    logger.info(f"HLS download complete: {output_file} ({total_segments} segments)")
    return output_file


# ──────────────────────────────────────────────
# Live Stream Recorder
# ──────────────────────────────────────────────

async def record_live_stream(
    rendition_url: str,
    output_path: str,
    filename: str,
    poll_interval: float = 2.0,
    progress_callback: Callable | None = None,
    stop_event: asyncio.Event | None = None,
) -> str:
    """
    Record a live HLS stream by polling for new segments.
    Stops when stop_event is set or when the stream ends.
    """
    if stop_event is None:
        stop_event = asyncio.Event()

    job_id = hashlib.md5(rendition_url.encode()).hexdigest()[:12]
    seg_dir = TEMP_DIR / f"live_{job_id}"
    seg_dir.mkdir(parents=True, exist_ok=True)

    seen_segments: set[str] = set()
    segment_count = 0
    total_bytes = 0
    start_time = time.monotonic()
    decryptor = AESDecryptor()

    async with aiohttp.ClientSession() as session:
        while not stop_event.is_set():
            try:
                async with session.get(rendition_url) as resp:
                    content = await resp.text()

                playlist = m3u8.loads(content, uri=rendition_url)

                for segment in playlist.segments:
                    seg_url = segment.absolute_uri
                    if seg_url in seen_segments:
                        continue

                    seen_segments.add(seg_url)

                    # Download segment
                    async with session.get(seg_url) as seg_resp:
                        data = await seg_resp.read()

                    # Decrypt if needed
                    if segment.key and segment.key.method == "AES-128":
                        key_url = segment.key.absolute_uri
                        iv = bytes.fromhex(segment.key.iv.replace("0x", "")) if segment.key.iv else struct.pack(">QQ", 0, segment_count)
                        key = await decryptor.fetch_key(key_url, session)
                        data = decryptor.decrypt(data, key, iv)

                    # Write to disk
                    seg_path = seg_dir / f"segment_{segment_count:06d}.ts"
                    with open(seg_path, "wb") as f:
                        f.write(data)

                    segment_count += 1
                    total_bytes += len(data)

                    if progress_callback:
                        elapsed = time.monotonic() - start_time
                        await progress_callback({
                            "segments": segment_count,
                            "bytes": total_bytes,
                            "elapsed": elapsed,
                            "is_live": True,
                        })

                # Check if stream ended
                if playlist.is_endlist:
                    logger.info("Live stream ended (EXT-X-ENDLIST detected)")
                    break

            except Exception as e:
                logger.warning(f"Live stream poll error: {e}")

            await asyncio.sleep(poll_interval)

    # Mux recorded segments
    from backend.utils.ffmpeg_utils import concat_ts_segments

    output_file = os.path.join(output_path, filename)
    os.makedirs(output_path, exist_ok=True)
    await concat_ts_segments(str(seg_dir), output_file)

    # Cleanup
    import shutil
    shutil.rmtree(str(seg_dir), ignore_errors=True)

    logger.info(f"Live recording complete: {output_file} ({segment_count} segments, {total_bytes} bytes)")
    return output_file
