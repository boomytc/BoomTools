from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from desktop.app.services.output_service import OutputService, ZipCancelledError
from shared.contracts import TaskRecord


class ZipResultsWorker(QObject):
    result_ready = Signal(object)
    error_occurred = Signal(str)
    finished = Signal()

    def __init__(self, output_service: OutputService, records: list[TaskRecord], output_dir: Path | None) -> None:
        super().__init__()
        self._output_service = output_service
        self._records = list(records)
        self._output_dir = output_dir
        self._cancel_requested = False

    @Slot()
    def cancel(self) -> None:
        self._cancel_requested = True

    @Slot()
    def run(self) -> None:
        result = None
        try:
            result = self._output_service.zip_successful_outputs(
                self._records,
                self._output_dir,
                cancel_requested=lambda: self._cancel_requested,
            )
        except ZipCancelledError as exc:
            self.error_occurred.emit(str(exc))
        except Exception as exc:
            self.error_occurred.emit(f"打包失败：{exc}")
        finally:
            if result is not None:
                self.result_ready.emit(result)
            self.finished.emit()
