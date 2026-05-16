"""
DEEP DOWNLOADR — Core Download Engine
yt-dlp wrapper + aria2c multi-segment orchestrator + format analysis pipeline.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("deep-downloadr.downloader")

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

APP_DIR = Path.home() / ".deep-downloadr"
TEMP_DIR = APP_DIR / "tmp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Locate binaries — check bundled first, then system PATH
def _find_binary(name: str) -> str:
    """Find binary in bundled dir or system PATH."""
    bundled = APP_DIR / "bin" / name
    if bundled.exists():
        return str(bundled)
    system = shutil.which(name)
    if system:
        return system
    raise FileNotFoundError(f"{name} not found. Install it or place in {APP_DIR / 'bin'}")

def get_ytdlp() -> str:
    return _find_binary("yt-dlp")

def get_aria2c() -> str:
    return _find_binary("aria2c")

def get_ffmpeg() -> str:
    return _find_binary("ffmpeg")


# ──────────────────────────────────────────────
# Format Helpers
# ──────────────────────────────────────────────

def _format_filesize(size_bytes: int | None) -> str:
    if not size_bytes:
        return "Unknown"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def _parse_resolution(height: int | None) -> str:
    if not height:
        return "Unknown"
    labels = {2160: "4K", 1440: "2K", 1080: "1080p", 720: "720p",
              480: "480p", 360: "360p", 240: "240p", 144: "144p"}
    return labels.get(height, f"{height}p")


def _classify_format(fmt: dict[str, Any]) -> dict[str, Any]:
    """Classify a yt-dlp format into a structured representation."""
    vcodec = fmt.get("vcodec", "none")
    acodec = fmt.get("acodec", "none")
    has_video = vcodec != "none" and vcodec is not None
    has_audio = acodec != "none" and acodec is not None

    # Detect HDR
    dynamic_range = fmt.get("dynamic_range", "")
    is_hdr = "HDR" in str(dynamic_range).upper() if dynamic_range else False

    # Detect codec family
    codec_family = "Unknown"
    if has_video:
        vc = str(vcodec).lower()
        if "av01" in vc or "av1" in vc:
            codec_family = "AV1"
        elif "hev" in vc or "h265" in vc or "hevc" in vc:
            codec_family = "H.265"
        elif "avc" in vc or "h264" in vc:
            codec_family = "H.264"
        elif "vp9" in vc:
            codec_family = "VP9"
        elif "vp8" in vc:
            codec_family = "VP8"

    audio_codec_family = "Unknown"
    if has_audio:
        ac = str(acodec).lower()
        if "opus" in ac:
            audio_codec_family = "Opus"
        elif "aac" in ac:
            audio_codec_family = "AAC"
        elif "mp3" in ac or "mp4a.69" in ac:
            audio_codec_family = "MP3"
        elif "eac3" in ac or "ec-3" in ac:
            audio_codec_family = "EAC-3"
        elif "ac-3" in ac or "ac3" in ac:
            audio_codec_family = "AC-3"
        elif "flac" in ac:
            audio_codec_family = "FLAC"
        elif "vorbis" in ac:
            audio_codec_family = "Vorbis"

    return {
        "format_id": fmt.get("format_id", ""),
        "format_note": fmt.get("format_note", ""),
        "ext": fmt.get("ext", ""),
        "has_video": has_video,
        "has_audio": has_audio,
        "width": fmt.get("width"),
        "height": fmt.get("height"),
        "resolution": _parse_resolution(fmt.get("height")),
        "fps": fmt.get("fps"),
        "vcodec": vcodec,
        "acodec": acodec,
        "codec_family": codec_family,
        "audio_codec_family": audio_codec_family,
        "is_hdr": is_hdr,
        "dynamic_range": dynamic_range,
        "filesize": fmt.get("filesize") or fmt.get("filesize_approx"),
        "filesize_str": _format_filesize(fmt.get("filesize") or fmt.get("filesize_approx")),
        "tbr": fmt.get("tbr"),  # total bitrate
        "vbr": fmt.get("vbr"),  # video bitrate
        "abr": fmt.get("abr"),  # audio bitrate
        "asr": fmt.get("asr"),  # audio sample rate
        "channels": fmt.get("audio_channels"),
        "language": fmt.get("language"),
        "url": fmt.get("url", ""),
        "protocol": fmt.get("protocol", ""),
    }


# ──────────────────────────────────────────────
# URL Analysis
# ──────────────────────────────────────────────

async def analyze_url(url: str) -> dict[str, Any]:
    """
    Analyze a URL using yt-dlp --dump-json and return structured format data.
    """
    ytdlp = get_ytdlp()
    cmd = [
        ytdlp,
        "--dump-json",
        "--no-download",
        "--no-warnings",
        "--no-playlist",
        "--flat-playlist",
        url,
    ]

    logger.info(f"Analyzing URL: {url}")
    start = time.monotonic()

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        error_msg = stderr.decode("utf-8", errors="replace").strip()
        logger.error(f"yt-dlp analysis failed: {error_msg}")
        raise RuntimeError(f"URL analysis failed: {error_msg}")

    elapsed = time.monotonic() - start
    logger.info(f"Analysis completed in {elapsed:.2f}s")

    data = json.loads(stdout.decode("utf-8"))

    # Extract thumbnails with resolution hierarchy
    thumbnails = data.get("thumbnails", [])
    thumbnail_url = ""
    if thumbnails:
        # Sort by preference — larger first
        sorted_thumbs = sorted(
            thumbnails,
            key=lambda t: (t.get("preference", 0), t.get("width", 0) or 0),
            reverse=True,
        )
        thumbnail_url = sorted_thumbs[0].get("url", "")

    # Classify all formats
    raw_formats = data.get("formats", [])
    classified = [_classify_format(f) for f in raw_formats]

    # Separate video, audio, and combined streams
    video_formats = [f for f in classified if f["has_video"]]
    audio_formats = [f for f in classified if f["has_audio"] and not f["has_video"]]
    combined_formats = [f for f in classified if f["has_video"] and f["has_audio"]]

    # Group video by resolution
    video_by_res: dict[str, list] = {}
    for vf in video_formats:
        key = vf["resolution"]
        video_by_res.setdefault(key, []).append(vf)

    # Extract subtitles
    subtitles = {}
    for lang, subs in data.get("subtitles", {}).items():
        subtitles[lang] = [
            {"ext": s.get("ext", ""), "url": s.get("url", ""), "name": s.get("name", lang)}
            for s in subs
        ]
    for lang, subs in data.get("automatic_captions", {}).items():
        key = f"{lang} (auto)"
        subtitles[key] = [
            {"ext": s.get("ext", ""), "url": s.get("url", ""), "name": f"{lang} (auto-generated)"}
            for s in subs
        ]

    # Chapter data
    chapters = [
        {"title": ch.get("title", ""), "start": ch.get("start_time", 0), "end": ch.get("end_time", 0)}
        for ch in data.get("chapters", [])
    ]

    return {
        "title": data.get("title", "Untitled"),
        "thumbnail": thumbnail_url,
        "thumbnails": [{"url": t.get("url"), "width": t.get("width"), "height": t.get("height")} for t in thumbnails],
        "duration": data.get("duration"),
        "uploader": data.get("uploader", data.get("channel", "")),
        "uploader_id": data.get("uploader_id", data.get("channel_id", "")),
        "upload_date": data.get("upload_date", ""),
        "view_count": data.get("view_count"),
        "like_count": data.get("like_count"),
        "description": (data.get("description") or "")[:2000],  # Truncate long descriptions
        "tags": data.get("tags", []),
        "categories": data.get("categories", []),
        "chapters": chapters,
        "formats": classified,
        "video_formats": video_formats,
        "audio_formats": audio_formats,
        "combined_formats": combined_formats,
        "video_by_resolution": video_by_res,
        "subtitles": subtitles,
        "source_id": data.get("id", ""),
        "webpage_url": data.get("webpage_url", url),
        "extractor": data.get("extractor", ""),
        "metadata": {
            "age_limit": data.get("age_limit"),
            "is_live": data.get("is_live", False),
            "was_live": data.get("was_live", False),
            "availability": data.get("availability"),
        },
    }


# ──────────────────────────────────────────────
# aria2c Multi-Segment Download
# ──────────────────────────────────────────────

@dataclass
class DownloadProgress:
    download_id: str
    progress: float = 0.0
    speed: float = 0.0
    downloaded: int = 0
    total: int = 0
    eta: int | None = None
    status: str = "downloading"


async def download_with_aria2c(
    url: str,
    output_path: str,
    filename: str,
    connections: int = 16,
    chunk_size: str = "1M",
    progress_callback: Any = None,
) -> str:
    """
    Download a URL using aria2c with multi-segment acceleration.
    Returns the path to the downloaded file.
    """
    aria2c = get_aria2c()

    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    full_path = output_dir / filename

    cmd = [
        aria2c,
        f"--max-connection-per-server={connections}",
        f"--split={connections}",
        f"--min-split-size={chunk_size}",
        "--file-allocation=falloc",
        "--continue=true",
        "--auto-file-renaming=false",
        "--allow-overwrite=true",
        "--summary-interval=1",
        "--console-log-level=notice",
        f"--dir={output_dir}",
        f"--out={filename}",
        url,
    ]

    logger.info(f"Starting aria2c download: {filename} ({connections} connections)")

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    # Parse aria2c output for progress
    progress_re = re.compile(
        r"\[.*?(\d+(?:\.\d+)?[KMGT]?i?B)/(\d+(?:\.\d+)?[KMGT]?i?B).*?"
        r"DL:(\d+(?:\.\d+)?[KMGT]?i?B)"
    )

    async for line in proc.stdout:  # type: ignore
        text = line.decode("utf-8", errors="replace").strip()
        if progress_callback:
            match = progress_re.search(text)
            if match:
                # Simple progress parsing — aria2c progress lines
                pass  # Progress updates via callback
        logger.debug(f"aria2c: {text}")

    await proc.wait()

    if proc.returncode != 0:
        raise RuntimeError(f"aria2c download failed with exit code {proc.returncode}")

    logger.info(f"Download complete: {full_path}")
    return str(full_path)


# ──────────────────────────────────────────────
# yt-dlp Direct Download
# ──────────────────────────────────────────────

async def download_with_ytdlp(
    url: str,
    output_path: str,
    format_id: str | None = None,
    quality: str = "best",
    embed_metadata: bool = True,
    embed_thumbnail: bool = True,
    progress_callback: Any = None,
) -> str:
    """
    Download media using yt-dlp with optional format selection.
    Returns path to the downloaded file.
    """
    ytdlp = get_ytdlp()

    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    template = str(output_dir / "%(title)s.%(ext)s")

    cmd = [
        ytdlp,
        "--no-warnings",
        "--newline",  # Progress on new lines for easier parsing
        "-o", template,
    ]

    # Format selection
    if format_id:
        cmd.extend(["-f", format_id])
    elif quality == "best":
        cmd.extend(["-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"])
    else:
        cmd.extend(["-f", f"bestvideo[height<={quality.replace('p', '')}]+bestaudio/best"])

    # Post-processing
    if embed_metadata:
        cmd.append("--embed-metadata")
    if embed_thumbnail:
        cmd.append("--embed-thumbnail")

    # Merge to MP4
    cmd.extend(["--merge-output-format", "mp4"])

    # External downloader — use aria2c for speed if available
    try:
        aria2c = get_aria2c()
        cmd.extend([
            "--downloader", aria2c,
            "--downloader-args", "aria2c:-x 16 -s 16 -k 1M",
        ])
    except FileNotFoundError:
        pass  # Fall back to yt-dlp's internal downloader

    cmd.append(url)

    logger.info(f"Starting yt-dlp download: {url}")

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    downloaded_file = ""
    progress_re = re.compile(r"\[download\]\s+(\d+(?:\.\d+)?)%\s+of\s+~?\s*([\d.]+\w+)")
    merge_re = re.compile(r"\[Merger\]\s+Merging formats into \"(.+?)\"")
    dest_re = re.compile(r"\[download\]\s+Destination:\s+(.+)")

    async for line in proc.stdout:  # type: ignore
        text = line.decode("utf-8", errors="replace").strip()
        logger.debug(f"yt-dlp: {text}")

        # Track destination file
        dest_match = dest_re.search(text)
        if dest_match:
            downloaded_file = dest_match.group(1)

        # Track merged output
        merge_match = merge_re.search(text)
        if merge_match:
            downloaded_file = merge_match.group(1)

        # Progress callback
        if progress_callback:
            prog_match = progress_re.search(text)
            if prog_match:
                pct = float(prog_match.group(1))
                await progress_callback(pct)

    await proc.wait()

    if proc.returncode != 0:
        raise RuntimeError(f"yt-dlp download failed with exit code {proc.returncode}")

    logger.info(f"yt-dlp download complete: {downloaded_file}")
    return downloaded_file


# ──────────────────────────────────────────────
# Adaptive Connection Optimizer
# ──────────────────────────────────────────────

async def measure_server_speed(url: str, sample_bytes: int = 65536) -> float:
    """
    Measure server response time by downloading a small sample.
    Returns estimated latency in seconds.
    """
    import aiohttp

    try:
        async with aiohttp.ClientSession() as session:
            start = time.monotonic()
            async with session.get(url, headers={"Range": f"bytes=0-{sample_bytes}"}) as resp:
                await resp.read()
            return time.monotonic() - start
    except Exception as e:
        logger.warning(f"Speed measurement failed: {e}")
        return 1.0  # Default 1s latency


async def optimize_connections(url: str) -> tuple[int, str]:
    """
    Dynamically determine optimal connection count and chunk size
    based on server response characteristics.
    Returns (connections, chunk_size).
    """
    latency = await measure_server_speed(url)

    if latency < 0.1:
        # Very fast server — many small connections
        return 32, "512K"
    elif latency < 0.3:
        return 24, "1M"
    elif latency < 0.8:
        return 16, "2M"
    else:
        # Slow server — fewer connections, larger chunks
        return 8, "4M"


# ──────────────────────────────────────────────
# CDN Mirror Selection
# ──────────────────────────────────────────────

async def select_fastest_mirror(urls: list[str]) -> str:
    """
    Select the fastest CDN mirror by timing HEAD requests.
    """
    import aiohttp

    if len(urls) <= 1:
        return urls[0] if urls else ""

    async def time_url(url: str) -> tuple[str, float]:
        try:
            async with aiohttp.ClientSession() as session:
                start = time.monotonic()
                async with session.head(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    return url, time.monotonic() - start
        except Exception:
            return url, 999.0

    results = await asyncio.gather(*[time_url(u) for u in urls])
    fastest = min(results, key=lambda x: x[1])
    logger.info(f"Selected fastest mirror: {fastest[0]} ({fastest[1]:.3f}s)")
    return fastest[0]


# ──────────────────────────────────────────────
# Auto-update yt-dlp
# ──────────────────────────────────────────────

async def auto_update_ytdlp() -> bool:
    """Run yt-dlp -U in background to update extractors."""
    try:
        ytdlp = get_ytdlp()
        proc = await asyncio.create_subprocess_exec(
            ytdlp, "-U",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode("utf-8", errors="replace")
        if "Updated" in output or "up to date" in output.lower():
            logger.info(f"yt-dlp update check: {output.strip()}")
            return True
        return False
    except Exception as e:
        logger.warning(f"yt-dlp auto-update failed: {e}")
        return False
