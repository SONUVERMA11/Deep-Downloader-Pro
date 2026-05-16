"""
DEEP DOWNLOADR — Duplicate Detector
Cross-source deduplication using SHA256 (sampled), filename, and size matching.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from backend.core.resume_engine import compute_sampled_hash
from backend.db.models import Download, DownloadStatus, FileIndex, get_session

logger = logging.getLogger("deep-downloadr.dedup")


class DuplicateDetector:
    """Detects duplicate files across all download sources."""

    def __init__(self):
        self.session = get_session()

    def check_duplicate(
        self,
        filename: str,
        file_size: int,
        content_hash: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Check if a file is a duplicate.
        Returns match info or None.
        """
        # Method 1: Exact hash match (highest confidence)
        if content_hash:
            match = (
                self.session.query(FileIndex)
                .filter_by(sha256_sampled=content_hash)
                .first()
            )
            if match:
                return {
                    "match_type": "hash",
                    "confidence": "exact",
                    "existing_path": match.file_path,
                    "existing_size": match.file_size,
                    "action": "skip",
                }

        # Method 2: Filename + size match (within 1% tolerance)
        name_only = os.path.splitext(filename)[0].lower()
        candidates = (
            self.session.query(FileIndex)
            .filter(FileIndex.file_name.ilike(f"%{name_only}%"))
            .all()
        )

        for c in candidates:
            if c.file_size and file_size:
                ratio = min(c.file_size, file_size) / max(c.file_size, file_size)
                if ratio > 0.99:
                    return {
                        "match_type": "name_size",
                        "confidence": "high",
                        "existing_path": c.file_path,
                        "existing_size": c.file_size,
                        "action": "skip",
                    }
                elif ratio > 0.5 and c.file_name.lower() == filename.lower():
                    return {
                        "match_type": "name_different_size",
                        "confidence": "medium",
                        "existing_path": c.file_path,
                        "existing_size": c.file_size,
                        "action": "prompt",
                    }

        # Method 3: Check download history
        history = (
            self.session.query(Download)
            .filter_by(status=DownloadStatus.COMPLETED)
            .filter(Download.title.ilike(f"%{name_only}%"))
            .first()
        )
        if history:
            return {
                "match_type": "history",
                "confidence": "medium",
                "existing_path": history.output_path,
                "download_id": history.download_id,
                "action": "prompt",
            }

        return None

    def index_file(
        self,
        file_path: str,
        source: str = "download",
        download_id: str | None = None,
    ) -> None:
        """Add a file to the dedup index."""
        try:
            if not os.path.exists(file_path):
                return

            stat = os.stat(file_path)
            sampled_hash = compute_sampled_hash(file_path)

            # Upsert
            existing = (
                self.session.query(FileIndex)
                .filter_by(file_path=file_path)
                .first()
            )

            if existing:
                existing.file_size = stat.st_size
                existing.sha256_sampled = sampled_hash
                existing.source = source
                existing.download_id = download_id
            else:
                entry = FileIndex(
                    file_path=file_path,
                    file_name=os.path.basename(file_path),
                    file_size=stat.st_size,
                    sha256_sampled=sampled_hash,
                    source=source,
                    download_id=download_id,
                )
                self.session.add(entry)

            self.session.commit()
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to index file {file_path}: {e}")

    def scan_directory(self, directory: str, source: str = "scan") -> int:
        """Recursively scan a directory and index all files."""
        count = 0
        for root, _, files in os.walk(directory):
            for f in files:
                fp = os.path.join(root, f)
                self.index_file(fp, source=source)
                count += 1
        logger.info(f"Indexed {count} files from {directory}")
        return count
