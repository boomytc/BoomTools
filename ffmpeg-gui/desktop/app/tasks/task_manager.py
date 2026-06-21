from __future__ import annotations

from desktop.app.runtime.ffmpeg import CommandSpec
from desktop.app.tasks.ffmpeg_process import FfmpegProcessWorker


class TaskManager:
    def __init__(self) -> None:
        self.current_worker: FfmpegProcessWorker | None = None
        self._cancel_batch_queue: bool = False

    def create_worker(self, spec: CommandSpec, duration_seconds: float | None) -> FfmpegProcessWorker:
        self.current_worker = FfmpegProcessWorker(spec, duration_seconds)
        return self.current_worker

    def cancel_current(self, *, preserve_batch_cancel: bool = False, wait: bool = False) -> None:
        if not preserve_batch_cancel:
            self._cancel_batch_queue = False
        if self.current_worker:
            if wait:
                self.current_worker.cancel_and_wait()
            else:
                self.current_worker.cancel()
            return
        self.current_worker = None

    def request_cancel_batch(self) -> None:
        self._cancel_batch_queue = True
        if self.current_worker:
            self.current_worker.cancel()

    def batch_cancel_requested(self) -> bool:
        return self._cancel_batch_queue

    def clear_batch_cancel_flag(self) -> None:
        self._cancel_batch_queue = False

    def clear_current(self, worker: FfmpegProcessWorker) -> None:
        if self.current_worker is worker:
            self.current_worker = None
