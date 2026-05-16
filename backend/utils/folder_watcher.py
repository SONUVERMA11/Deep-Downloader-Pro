"""
DEEP DOWNLOADR — Folder Watcher
Live destination monitoring using watchdog for automatic file indexing.
"""

from __future__ import annotations

import logging
import os
from typing import Callable

logger = logging.getLogger("deep-downloadr.watcher")


class FolderWatcher:
    """Watches download directories for file changes."""

    def __init__(self, paths: list[str], on_file_added: Callable | None = None):
        self.paths = paths
        self.on_file_added = on_file_added
        self._observer = None

    def start(self) -> None:
        """Start watching directories."""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            class Handler(FileSystemEventHandler):
                def __init__(self, callback):
                    self.callback = callback

                def on_created(self, event):
                    if not event.is_directory and self.callback:
                        self.callback(event.src_path)

                def on_modified(self, event):
                    if not event.is_directory and self.callback:
                        self.callback(event.src_path)

            self._observer = Observer()
            handler = Handler(self.on_file_added)

            for path in self.paths:
                if os.path.isdir(path):
                    self._observer.schedule(handler, path, recursive=True)
                    logger.info(f"Watching directory: {path}")

            self._observer.start()
        except ImportError:
            logger.warning("watchdog not installed, folder watching disabled")

    def stop(self) -> None:
        if self._observer:
            self._observer.stop()
            self._observer.join()
