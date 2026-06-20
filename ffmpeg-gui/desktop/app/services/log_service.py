from __future__ import annotations

from datetime import datetime
from pathlib import Path

from desktop.app.core.paths import LOGS_DIR, ensure_runtime_dirs
from shared.contracts import TaskRecord


class LogService:
    def save_task_log(self, task: TaskRecord, lines: list[str]) -> Path:
        ensure_runtime_dirs()
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = LOGS_DIR / f"{timestamp}_{task.task_id}.log"
        content = "\n".join(lines)
        if content:
            content += "\n"
        path.write_text(content, encoding="utf-8")
        return path
