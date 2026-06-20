from __future__ import annotations

import asyncio
import json
import shutil
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import ToolConfig
from .ffmpeg import CommandError, build_command, media_duration_seconds, parse_progress_line, probe_media
from .schemas import JobResponse, JobStatus, Operation


TERMINAL_STATUSES = {JobStatus.succeeded, JobStatus.failed, JobStatus.cancelled}


@dataclass
class Job:
    job_id: str
    file_id: str
    operation: Operation
    options: dict[str, Any]
    input_path: Path
    upload_dir: Path
    job_dir: Path
    status: JobStatus = JobStatus.pending
    progress: float | None = 0.0
    message: str = "Queued"
    logs: deque[str] = field(default_factory=lambda: deque(maxlen=120))
    output_path: Path | None = None
    output_name: str | None = None
    process: asyncio.subprocess.Process | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    media_duration: float | None = None

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    def to_response(self) -> JobResponse:
        output_size = self.output_path.stat().st_size if self.output_path and self.output_path.exists() else None
        download_url = f"/api/jobs/{self.job_id}/download" if self.status == JobStatus.succeeded else None
        return JobResponse(
            job_id=self.job_id,
            status=self.status,
            operation=self.operation,
            progress=self.progress,
            message=self.message,
            logs_tail=list(self.logs)[-80:],
            output_name=self.output_name,
            output_size=output_size,
            download_url=download_url,
        )


class JobManager:
    def __init__(self, config: ToolConfig) -> None:
        self.config = config
        self.jobs: dict[str, Job] = {}
        self.subscribers: dict[str, set[asyncio.Queue[str]]] = {}
        self.semaphore = asyncio.Semaphore(1)

    def create_job(
        self,
        *,
        file_id: str,
        operation: Operation,
        options: dict[str, Any],
        input_path: Path,
        upload_dir: Path,
    ) -> Job:
        job_id = uuid.uuid4().hex
        job_dir = self.config.jobs_root / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        job = Job(
            job_id=job_id,
            file_id=file_id,
            operation=operation,
            options=options,
            input_path=input_path,
            upload_dir=upload_dir,
            job_dir=job_dir,
        )
        self.jobs[job_id] = job
        self._publish(job)
        asyncio.create_task(self._run_job(job))
        return job

    def get_job(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    async def delete_job(self, job_id: str) -> bool:
        job = self.jobs.pop(job_id, None)
        if not job:
            return False
        if job.process and job.status == JobStatus.running:
            job.status = JobStatus.cancelled
            job.message = "Cancelled"
            try:
                job.process.terminate()
            except ProcessLookupError:
                pass
        shutil.rmtree(job.job_dir, ignore_errors=True)
        shutil.rmtree(job.upload_dir, ignore_errors=True)
        self._publish(job)
        self.subscribers.pop(job_id, None)
        return True

    def subscribe(self, job_id: str) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=20)
        self.subscribers.setdefault(job_id, set()).add(queue)
        job = self.jobs.get(job_id)
        if job:
            queue.put_nowait(self._event_payload(job))
        return queue

    def unsubscribe(self, job_id: str, queue: asyncio.Queue[str]) -> None:
        subscribers = self.subscribers.get(job_id)
        if not subscribers:
            return
        subscribers.discard(queue)
        if not subscribers:
            self.subscribers.pop(job_id, None)

    async def _run_job(self, job: Job) -> None:
        async with self.semaphore:
            if job.status == JobStatus.cancelled:
                return
            await self._execute(job)

    async def _execute(self, job: Job) -> None:
        try:
            media_info = await probe_media(self.config.ffprobe_bin, job.input_path)
            job.media_duration = media_duration_seconds(media_info)
            spec = build_command(
                ffmpeg_bin=self.config.ffmpeg_bin,
                operation=job.operation.value,
                options=job.options,
                input_path=job.input_path,
                output_dir=job.job_dir,
                asset_path=_resolve_asset_path(job),
            )
        except CommandError as exc:
            self._fail(job, str(exc))
            return

        job.output_path = spec.output_path
        job.output_name = spec.output_name
        job.status = JobStatus.running
        job.progress = 0.0 if job.media_duration else None
        job.message = "Running ffmpeg"
        job.logs.append("$ " + " ".join(_quote_arg(arg) for arg in spec.args))
        job.touch()
        self._publish(job)

        proc = await asyncio.create_subprocess_exec(
            *spec.args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        job.process = proc
        await asyncio.gather(self._read_progress(job, proc), self._read_logs(job, proc))
        return_code = await proc.wait()
        job.process = None

        if job.status == JobStatus.cancelled:
            self._publish(job)
            return
        if return_code == 0 and spec.output_path.exists():
            job.status = JobStatus.succeeded
            job.progress = 1.0
            job.message = "Finished"
            job.touch()
            self._publish(job)
            return
        self._fail(job, f"ffmpeg exited with code {return_code}")

    async def _read_progress(self, job: Job, proc: asyncio.subprocess.Process) -> None:
        if not proc.stdout:
            return
        while True:
            raw = await proc.stdout.readline()
            if not raw:
                break
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            if line == "progress=end":
                job.progress = 1.0
            else:
                progress = parse_progress_line(line, job.media_duration)
                if progress is not None:
                    job.progress = progress
            job.touch()
            self._publish(job)

    async def _read_logs(self, job: Job, proc: asyncio.subprocess.Process) -> None:
        if not proc.stderr:
            return
        while True:
            raw = await proc.stderr.readline()
            if not raw:
                break
            line = raw.decode("utf-8", errors="replace").rstrip()
            if line:
                job.logs.append(line)
                job.touch()
                self._publish(job)

    def _fail(self, job: Job, message: str) -> None:
        job.status = JobStatus.failed
        job.message = message
        job.touch()
        self._publish(job)

    def _publish(self, job: Job) -> None:
        payload = self._event_payload(job)
        for queue in list(self.subscribers.get(job.job_id, set())):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(payload)

    def _event_payload(self, job: Job) -> str:
        return json.dumps(job.to_response().model_dump(mode="json"), ensure_ascii=False)


def _quote_arg(arg: str) -> str:
    if not arg or any(ch.isspace() for ch in arg):
        return '"' + arg.replace('"', '\\"') + '"'
    return arg


def _resolve_asset_path(job: Job) -> Path | None:
    if job.operation is not Operation.subtitles:
        return None
    asset_id = str(job.options.get("asset_id", "")).strip()
    if not asset_id:
        return None
    asset_dir = job.upload_dir / "assets"
    if not asset_dir.exists():
        return None
    matches = sorted(asset_dir.glob(f"{asset_id}.*"))
    return matches[0] if matches else None
