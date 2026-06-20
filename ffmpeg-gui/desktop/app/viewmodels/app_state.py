from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from desktop.app.runtime.binaries import RuntimeHealth
from shared.contracts import MediaInfo, TaskRecord, TaskStatus


@dataclass
class AppState:
    input_path: Path | None = None
    output_dir: Path | None = None
    media_info: MediaInfo | None = None
    runtime_health: RuntimeHealth | None = None
    current_task: TaskRecord | None = None
    logs: list[str] = field(default_factory=list)
    error_message: str | None = None

    def can_start(self) -> bool:
        if not self.input_path or not self.input_path.exists():
            return False
        if self.current_task and self.current_task.status is TaskStatus.running:
            return False
        return bool(self.runtime_health and self.runtime_health.ok)

    def set_media_info(self, raw: dict[str, Any], duration_seconds: float | None) -> None:
        self.media_info = MediaInfo(raw=raw, duration_seconds=duration_seconds)
