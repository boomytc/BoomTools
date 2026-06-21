from __future__ import annotations

import subprocess
from pathlib import Path
from threading import Lock

from PySide6.QtCore import QObject, Signal, Slot

from desktop.app.runtime.binaries import binary_available
from desktop.app.runtime.probe import build_probe_command, media_info_from_probe_output
from desktop.app.services.ffmpeg_service import FfmpegService
from shared.contracts import MediaInfo


class ProbeWorker(QObject):
    media_info_ready = Signal(object, object)
    error_occurred = Signal(object, str)
    finished = Signal()

    def __init__(self, _service: FfmpegService, ffprobe_bin: str, input_path: Path) -> None:
        super().__init__()
        self._ffprobe_bin = ffprobe_bin
        self._input_path = input_path
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
            media_info = self._probe()
            if self._cancel_requested:
                return
            if media_info.has_error:
                self.error_occurred.emit(self._input_path, media_info.error_message or "ffprobe failed")
            self.media_info_ready.emit(self._input_path, media_info)
        except Exception as exc:  # noqa: BLE001 - convert worker failures to UI-safe text
            if not self._cancel_requested:
                self.error_occurred.emit(self._input_path, str(exc))
        finally:
            self.finished.emit()

    def _probe(self) -> MediaInfo:
        if not binary_available(self._ffprobe_bin):
            return MediaInfo(raw={"error": "ffprobe is not available"})
        if not self._input_path.exists():
            return MediaInfo(raw={"error": "input file does not exist"})
        if self._cancel_requested:
            return MediaInfo(raw={"error": "ffprobe cancelled"})

        command = build_probe_command(self._ffprobe_bin, self._input_path)
        # Arguments are constructed as an explicit array and never use a shell.
        process = subprocess.Popen(  # noqa: S603
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        with self._process_lock:
            self._process = process
        try:
            stdout, stderr = process.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            return MediaInfo(raw={"error": "ffprobe timed out"})
        finally:
            with self._process_lock:
                if self._process is process:
                    self._process = None

        return media_info_from_probe_output(
            stdout=stdout,
            stderr=stderr,
            returncode=process.returncode,
        )
