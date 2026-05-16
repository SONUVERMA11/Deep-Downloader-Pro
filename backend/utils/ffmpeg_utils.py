"""
DEEP DOWNLOADR — FFmpeg Utilities
Muxing, remuxing, metadata embedding, and thumbnail operations.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("deep-downloadr.ffmpeg")


def _find_ffmpeg() -> str:
    """Find ffmpeg binary."""
    app_dir = Path.home() / ".deep-downloadr" / "bin"
    bundled = app_dir / "ffmpeg"
    if bundled.exists():
        return str(bundled)
    system = shutil.which("ffmpeg")
    if system:
        return system
    raise FileNotFoundError("FFmpeg not found")


def _find_ffprobe() -> str:
    """Find ffprobe binary."""
    app_dir = Path.home() / ".deep-downloadr" / "bin"
    bundled = app_dir / "ffprobe"
    if bundled.exists():
        return str(bundled)
    system = shutil.which("ffprobe")
    if system:
        return system
    raise FileNotFoundError("FFprobe not found")


async def get_media_info(file_path: str) -> dict[str, Any]:
    """Get media info via ffprobe."""
    ffprobe = _find_ffprobe()
    cmd = [
        ffprobe,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    return json.loads(stdout.decode("utf-8"))


async def mux_video_audio(
    video_path: str,
    audio_path: str,
    output_path: str,
    container: str = "mp4",
    metadata: dict[str, str] | None = None,
    thumbnail_path: str | None = None,
) -> str:
    """
    Mux separate video and audio streams into a single container.
    Optionally embeds metadata and thumbnail.
    """
    ffmpeg = _find_ffmpeg()
    cmd = [ffmpeg, "-y", "-i", video_path, "-i", audio_path]

    input_idx = 2  # next input index

    # Add thumbnail if provided
    if thumbnail_path and os.path.exists(thumbnail_path):
        cmd.extend(["-i", thumbnail_path])
        input_idx += 1

    # Map streams
    cmd.extend(["-map", "0:v:0", "-map", "1:a:0"])

    if thumbnail_path and os.path.exists(thumbnail_path):
        cmd.extend(["-map", "2:0", "-disposition:v:1", "attached_pic"])

    # Copy codecs (no re-encoding)
    cmd.extend(["-c:v", "copy", "-c:a", "copy"])

    # Add metadata
    if metadata:
        for key, value in metadata.items():
            if value:
                cmd.extend(["-metadata", f"{key}={value}"])

    # Output
    cmd.extend(["-movflags", "+faststart", output_path])

    logger.info(f"Muxing: {os.path.basename(video_path)} + {os.path.basename(audio_path)}")

    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        error = stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"FFmpeg mux failed: {error}")

    logger.info(f"Mux complete: {output_path}")
    return output_path


async def embed_metadata(
    file_path: str,
    metadata: dict[str, str],
    thumbnail_path: str | None = None,
    chapters: list[dict] | None = None,
) -> str:
    """
    Embed metadata tags and optional thumbnail into an existing media file.
    Creates a new file and replaces the original.
    """
    ffmpeg = _find_ffmpeg()
    temp_output = file_path + ".tmp.mp4"

    cmd = [ffmpeg, "-y", "-i", file_path]

    if thumbnail_path and os.path.exists(thumbnail_path):
        cmd.extend(["-i", thumbnail_path])

    cmd.extend(["-map", "0", "-c", "copy"])

    if thumbnail_path and os.path.exists(thumbnail_path):
        cmd.extend(["-map", "1:0", "-disposition:v:1", "attached_pic"])

    # Metadata tags
    for key, value in metadata.items():
        if value:
            cmd.extend(["-metadata", f"{key}={value}"])

    cmd.extend(["-movflags", "+faststart", temp_output])

    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    await proc.communicate()

    if proc.returncode == 0:
        os.replace(temp_output, file_path)
        logger.info(f"Metadata embedded: {file_path}")
    else:
        if os.path.exists(temp_output):
            os.remove(temp_output)
        logger.warning(f"Metadata embedding failed for {file_path}")

    return file_path


async def concat_ts_segments(
    segment_dir: str,
    output_path: str,
    segment_pattern: str = "segment_%05d.ts",
) -> str:
    """
    Concatenate .ts segments into a single file using FFmpeg concat.
    Memory-efficient: reads from disk, never buffers all in RAM.
    """
    ffmpeg = _find_ffmpeg()

    # Build concat file list
    segments = sorted(
        [f for f in os.listdir(segment_dir) if f.endswith(".ts")],
        key=lambda x: x,
    )

    if not segments:
        raise ValueError(f"No .ts segments found in {segment_dir}")

    concat_file = os.path.join(segment_dir, "concat.txt")
    with open(concat_file, "w") as f:
        for seg in segments:
            f.write(f"file '{os.path.join(segment_dir, seg)}'\n")

    cmd = [
        ffmpeg, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        "-movflags", "+faststart",
        output_path,
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()

    # Cleanup
    os.remove(concat_file)

    if proc.returncode != 0:
        error = stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"FFmpeg concat failed: {error}")

    logger.info(f"Concat complete: {output_path} ({len(segments)} segments)")
    return output_path
