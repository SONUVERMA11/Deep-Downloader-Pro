"""
DEEP DOWNLOADR — Scheduler
Cron-based scheduling for downloads, playlist syncs, and scans.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger("deep-downloadr.scheduler")


class Scheduler:
    """Simple async task scheduler for periodic jobs."""

    def __init__(self):
        self.jobs: dict[str, dict[str, Any]] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._running = False

    def add_job(
        self,
        job_id: str,
        callback: Callable,
        interval_hours: float = 6,
        name: str = "",
        payload: dict | None = None,
    ) -> None:
        """Add a recurring job."""
        self.jobs[job_id] = {
            "id": job_id,
            "name": name or job_id,
            "callback": callback,
            "interval": interval_hours * 3600,
            "payload": payload or {},
            "enabled": True,
            "last_run": None,
            "next_run": None,
        }

    def remove_job(self, job_id: str) -> None:
        task = self._tasks.pop(job_id, None)
        if task:
            task.cancel()
        self.jobs.pop(job_id, None)

    async def start(self) -> None:
        """Start all scheduled jobs."""
        self._running = True
        for job_id, job in self.jobs.items():
            if job["enabled"]:
                self._tasks[job_id] = asyncio.create_task(
                    self._run_job_loop(job_id)
                )
        logger.info(f"Scheduler started with {len(self._tasks)} jobs")

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks.values():
            task.cancel()
        self._tasks.clear()

    async def _run_job_loop(self, job_id: str) -> None:
        job = self.jobs[job_id]
        while self._running and job["enabled"]:
            try:
                logger.info(f"Running scheduled job: {job['name']}")
                job["last_run"] = datetime.now(timezone.utc)

                if asyncio.iscoroutinefunction(job["callback"]):
                    await job["callback"](**job["payload"])
                else:
                    job["callback"](**job["payload"])

            except Exception as e:
                logger.error(f"Scheduled job {job_id} failed: {e}")

            await asyncio.sleep(job["interval"])

    def get_status(self) -> list[dict[str, Any]]:
        return [
            {
                "id": j["id"],
                "name": j["name"],
                "enabled": j["enabled"],
                "interval_hours": j["interval"] / 3600,
                "last_run": j["last_run"].isoformat() if j["last_run"] else None,
            }
            for j in self.jobs.values()
        ]
