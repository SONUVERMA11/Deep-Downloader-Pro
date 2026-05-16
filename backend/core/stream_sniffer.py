"""
DEEP DOWNLOADR — Stream Sniffer
Local mitmproxy interceptor for capturing HLS/M3U8 streams.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable

logger = logging.getLogger("deep-downloadr.sniffer")


class StreamSniffer:
    """Monitors local proxy traffic for streamable URLs."""

    def __init__(self, port: int = 8080):
        self.port = port
        self.captured_urls: list[dict[str, Any]] = []
        self.on_stream_detected: Callable | None = None
        self._running = False

        # Patterns to match
        self.patterns = [
            re.compile(r"\.m3u8(\?|$)", re.IGNORECASE),
            re.compile(r"/segment/", re.IGNORECASE),
            re.compile(r"/ts/", re.IGNORECASE),
            re.compile(r"chunklist", re.IGNORECASE),
            re.compile(r"\.ts(\?|$)", re.IGNORECASE),
        ]

    def check_url(self, url: str) -> bool:
        """Check if a URL matches stream patterns."""
        return any(p.search(url) for p in self.patterns)

    async def start(self) -> None:
        """Start the mitmproxy sniffer."""
        logger.info(f"Stream sniffer starting on 127.0.0.1:{self.port}")
        self._running = True
        # mitmproxy integration would go here
        # For now, this is a stub that can be connected to

    async def stop(self) -> None:
        self._running = False
        logger.info("Stream sniffer stopped")

    def get_captured(self) -> list[dict[str, Any]]:
        return self.captured_urls.copy()
