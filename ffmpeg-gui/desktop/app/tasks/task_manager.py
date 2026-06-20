from __future__ import annotations

from desktop.app.runtime.ffmpeg import CommandSpec
from desktop.app.tasks.ffmpeg_process import FfmpegProcessWorker


class TaskManager:
    def __init__(self) -> None:
        self.current_worker: FfmpegProcessWorker | None = None

    def create_worker(self, spec: CommandSpec, duration_seconds: float | None) -> FfmpegProcessWorker:
        self.current_worker = FfmpegProcessWorker(spec, duration_seconds)
        return self.current_worker

    def cancel_current(self) -> None:
        if self.current_worker:
            self.current_worker.cancel()

    def clear_current(self, worker: FfmpegProcessWorker) -> None:
        if self.current_worker is worker:
            self.current_worker = None
