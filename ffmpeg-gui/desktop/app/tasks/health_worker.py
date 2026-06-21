from __future__ import annotations

import subprocess
from threading import Lock

from PySide6.QtCore import QObject, Signal, Slot

from desktop.app.runtime.binaries import RuntimeHealth, runtime_health_snapshot


class HealthWorker(QObject):
    health_ready = Signal(str, str, object)
    finished = Signal()

    def __init__(self, ffmpeg_bin: str, ffprobe_bin: str) -> None:
        super().__init__()
        self._ffmpeg_bin = ffmpeg_bin
        self._ffprobe_bin = ffprobe_bin
        self._cancel_requested = False
        self._process: subprocess.Popen[str] | None = None
        self._process_lock = Lock()

    @Slot()
    def cancel(self) -> None:
        self._cancel_requested = True
        with self._process_lock:
            process = self._process
        if process is None or process.poll() is not None:
            return
        process.terminate()

    @Slot()
    def run(self) -> None:
        try:
            health = self._check_health()
            if not self._cancel_requested:
                self.health_ready.emit(self._ffmpeg_bin, self._ffprobe_bin, health)
        finally:
            self.finished.emit()

    def _check_health(self) -> RuntimeHealth:
        snapshot = runtime_health_snapshot(self._ffmpeg_bin, self._ffprobe_bin)
        if not snapshot.ffmpeg_available or self._cancel_requested:
            return snapshot
        return runtime_health_snapshot(
            self._ffmpeg_bin,
            self._ffprobe_bin,
            ffmpeg_version=self._ffmpeg_version(),
        )

    def _ffmpeg_version(self) -> str | None:
        try:
            process = subprocess.Popen(  # noqa: S603
                [self._ffmpeg_bin, "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError:
            return None
        with self._process_lock:
            self._process = process
        try:
            stdout, _stderr = process.communicate(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            process.kill()
            process.communicate()
            return None
        finally:
            with self._process_lock:
                if self._process is process:
                    self._process = None

        if process.returncode != 0:
            return None
        lines = stdout.splitlines()
        return lines[0] if lines else None
