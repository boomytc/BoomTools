from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from desktop.app.services.ffmpeg_service import FfmpegService
from shared.contracts import MediaInfo


class ProbeWorker(QObject):
    media_info_ready = Signal(object, object)
    error_occurred = Signal(object, str)
    finished = Signal()

    def __init__(self, service: FfmpegService, ffprobe_bin: str, input_path: Path) -> None:
        super().__init__()
        self._service = service
        self._ffprobe_bin = ffprobe_bin
        self._input_path = input_path

    @Slot()
    def run(self) -> None:
        try:
            media_info: MediaInfo = self._service.probe(self._ffprobe_bin, self._input_path)
            if media_info.has_error:
                self.error_occurred.emit(self._input_path, media_info.error_message or "ffprobe failed")
            self.media_info_ready.emit(self._input_path, media_info)
        except Exception as exc:  # noqa: BLE001 - convert worker failures to UI-safe text
            self.error_occurred.emit(self._input_path, str(exc))
        finally:
            self.finished.emit()
