"""
DEEP DOWNLOADR — Resume Engine
5-method detection system for resuming interrupted downloads.
Operates globally across all download sources.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("deep-downloadr.resume")


@dataclass
class ResumeCandidate:
    """A file that might be a partial/resumable download."""
    method: str  # "sidecar", "file_unique_id", "size_match", "name_match", "timestamp"
    confidence: str  # "high", "medium", "low"
    file_path: str
    expected_size: int
    current_size: int
    metadata: dict[str, Any]


from dataclasses import dataclass


def scan_for_sidecars(directory: str) -> list[dict[str, Any]]:
    """
    Method 1: Scan for .deepdl sidecar files — highest confidence.
    """
    results = []
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith(".deepdl"):
                sidecar_path = os.path.join(root, f)
                try:
                    with open(sidecar_path, "r") as fh:
                        data = json.load(fh)

                    media_path = sidecar_path[:-7]  # Remove .deepdl extension
                    file_exists = os.path.exists(media_path)
                    current_size = os.path.getsize(media_path) if file_exists else 0

                    results.append({
                        "method": "sidecar",
                        "confidence": "high",
                        "file_path": media_path,
                        "sidecar_path": sidecar_path,
                        "file_exists": file_exists,
                        "expected_size": data.get("expected_size", 0),
                        "current_size": current_size,
                        "progress_pct": data.get("progress_pct", 0),
                        "source": data.get("source", "unknown"),
                        "metadata": data,
                    })
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning(f"Invalid sidecar {sidecar_path}: {e}")

    return results


def match_by_file_unique_id(
    file_unique_id: str,
    db_session: Any,
) -> list[dict[str, Any]]:
    """
    Method 2: Match by Telegram file_unique_id in database.
    """
    from backend.db.models import TelegramDownload, Download

    results = []
    records = (
        db_session.query(TelegramDownload)
        .filter_by(file_unique_id=file_unique_id)
        .all()
    )

    for rec in records:
        dl = db_session.query(Download).filter_by(download_id=rec.download_id).first()
        if dl and dl.output_path:
            file_path = os.path.join(dl.output_path, dl.filename or "")
            results.append({
                "method": "file_unique_id",
                "confidence": "high",
                "file_path": file_path,
                "expected_size": rec.expected_size,
                "current_size": rec.bytes_written,
                "download_id": rec.download_id,
            })

    return results


def match_by_size(
    directory: str,
    expected_size: int,
    tolerance: int = 512,
) -> list[dict[str, Any]]:
    """
    Method 3: Find files smaller than expected size (likely partial).
    Tolerance: ±512 bytes.
    """
    results = []
    if not os.path.isdir(directory):
        return results

    for root, _, files in os.walk(directory):
        for f in files:
            fp = os.path.join(root, f)
            try:
                size = os.path.getsize(fp)
                if size < expected_size and (expected_size - size) > tolerance:
                    results.append({
                        "method": "size_match",
                        "confidence": "medium",
                        "file_path": fp,
                        "expected_size": expected_size,
                        "current_size": size,
                        "progress_pct": round(size / max(expected_size, 1) * 100, 1),
                    })
            except OSError:
                continue

    return results


def match_by_filename(
    directory: str,
    target_name: str,
) -> list[dict[str, Any]]:
    """
    Method 4: Normalized filename + extension match.
    """
    import unicodedata

    def normalize(name: str) -> str:
        name = unicodedata.normalize("NFC", name).lower()
        name = "".join(c for c in name if c.isalnum() or c in "._-")
        return name.replace("_", "").replace("-", "").replace(" ", "")

    target_norm = normalize(target_name)
    results = []

    if not os.path.isdir(directory):
        return results

    for root, _, files in os.walk(directory):
        for f in files:
            if normalize(f) == target_norm:
                fp = os.path.join(root, f)
                results.append({
                    "method": "name_match",
                    "confidence": "medium",
                    "file_path": fp,
                    "current_size": os.path.getsize(fp),
                })

    return results


def match_by_timestamp(
    directory: str,
    upload_time: datetime,
    expected_size: int,
    tolerance_seconds: int = 5,
) -> list[dict[str, Any]]:
    """
    Method 5: File modification time within ±5s of upload time AND size ≤ expected.
    Lowest confidence — always shown for manual review.
    """
    results = []
    if not os.path.isdir(directory):
        return results

    upload_ts = upload_time.timestamp()

    for root, _, files in os.walk(directory):
        for f in files:
            fp = os.path.join(root, f)
            try:
                stat = os.stat(fp)
                mtime = stat.st_mtime
                size = stat.st_size

                if abs(mtime - upload_ts) <= tolerance_seconds and size <= expected_size:
                    results.append({
                        "method": "timestamp",
                        "confidence": "low",
                        "file_path": fp,
                        "current_size": size,
                        "expected_size": expected_size,
                        "time_diff": abs(mtime - upload_ts),
                    })
            except OSError:
                continue

    return results


def compute_sampled_hash(file_path: str, sample_size: int = 1048576) -> str:
    """
    Compute SHA256 of first + last 1MB of a file for fast comparison.
    """
    h = hashlib.sha256()
    file_size = os.path.getsize(file_path)

    with open(file_path, "rb") as f:
        # First 1MB
        h.update(f.read(min(sample_size, file_size)))

        # Last 1MB (if file is large enough)
        if file_size > sample_size * 2:
            f.seek(-sample_size, 2)
            h.update(f.read(sample_size))

    return h.hexdigest()
