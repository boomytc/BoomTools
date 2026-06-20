from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class TaskSignals(QObject):
    progress_changed = Signal(object)
    status_changed = Signal(object)
    log_received = Signal(str)
    result_ready = Signal(object)
    error_occurred = Signal(str)
    finished = Signal(object)
