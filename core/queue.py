"""
Job Queue — Async task scheduling with prioritization and concurrency control.

Manages analysis jobs with:
- Priority-based scheduling (1-10)
- Configurable concurrency limits
- Job lifecycle (queued → running → completed/failed)
- Real-time status via websocket events
- Per-job token budgeting
"""

import asyncio
import logging
import uuid
from enum import Enum
from typing import Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("cortexflow.queue")


class JobStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    id: str
    name: str
    priority: int
    pipeline_config: dict
    status: JobStatus = JobStatus.QUEUED
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None
    token_budget: int = 100_000
    tokens_used: int = 0
    progress: float = 0.0
    current_stage: str = ""


class JobQueue:
    """Async job queue with priority scheduling."""

    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._active: dict[str, Job] = {}
        self._completed: dict[str, Job] = {}
        self._history: list[Job] = []
        self._running_count = 0
        self._lock = asyncio.Lock()
        self._subscribers: list[Callable] = []
        self._processor_task: Optional[asyncio.Task] = None

    async def _notify(self, event: str, job: Job):
        for cb in self._subscribers:
            try:
                await cb(event, job)
            except Exception as e:
                logger.error(f"Subscriber error: {e}")

    async def enqueue(self, name: str, pipeline_config: dict,
                      priority: int = 5, token_budget: int = 100_000) -> str:
        """Add a new analysis job to the queue."""
        job = Job(
            id=str(uuid.uuid4())[:8],
            name=name,
            priority=priority,
            pipeline_config=pipeline_config,
            created_at=datetime.utcnow().isoformat(),
            token_budget=token_budget,
        )
        await self._queue.put((-priority, job.created_at, job))
        self._history.append(job)
        await self._notify("enqueued", job)
        logger.info(f"Job {job.id} enqueued (priority={priority})")
        return job.id

    async def start(self):
        """Start the queue processor."""
        if self._processor_task is None:
            self._processor_task = asyncio.create_task(self._process())
            logger.info("Queue processor started")

    async def stop(self):
        """Stop the queue processor."""
        if self._processor_task:
            self._processor_task.cancel()
            self._processor_task = None

    async def _process(self):
        """Main queue processing loop."""
        while True:
            if self._running_count >= self.max_concurrent:
                await asyncio.sleep(0.5)
                continue

            try:
                _, _, job = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            async with self._lock:
                self._running_count += 1
                job.status = JobStatus.RUNNING
                job.started_at = datetime.utcnow().isoformat()
                self._active[job.id] = job

            await self._notify("started", job)

            # In production, this would call the Pipeline executor
            asyncio.create_task(self._execute_job(job))

    async def _execute_job(self, job: Job):
        """Execute a single job (pipeline call in production)."""
        try:
            job.progress = 0.0
            job.current_stage = "initializing"

            # Simulated pipeline execution
            stages = ["analysis", "scanning", "report"]
            total = len(stages)

            for i, stage in enumerate(stages):
                job.current_stage = stage
                job.progress = (i / total) * 100
                await self._notify("progress", job)
                await asyncio.sleep(0.1)

            job.progress = 100.0
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow().isoformat()
            job.result = {"stages_completed": stages}
            await self._notify("completed", job)

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.utcnow().isoformat()
            await self._notify("failed", job)
            logger.error(f"Job {job.id} failed: {e}")

        finally:
            async with self._lock:
                self._running_count -= 1
                self._completed[job.id] = job
                self._active.pop(job.id, None)

    def get_status(self, job_id: str) -> Optional[Job]:
        """Get job status by ID."""
        return (self._active.get(job_id) or
                self._completed.get(job_id))

    def get_active(self) -> list[Job]:
        return list(self._active.values())

    def stats(self) -> dict:
        return {
            "active": len(self._active),
            "completed": len(self._completed),
            "queued": self._queue.qsize(),
            "history": len(self._history),
            "running_count": self._running_count,
        }

    def subscribe(self, callback: Callable):
        self._subscribers.append(callback)

    def cancel(self, job_id: str) -> bool:
        job = self._active.get(job_id)
        if job and job.status == JobStatus.RUNNING:
            job.status = JobStatus.CANCELLED
            return True
        return False

