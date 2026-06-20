from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from desktop.app.runtime.binaries import RuntimeHealth
from shared.contracts import MediaInfo, TaskRecord, TaskStatus


@dataclass
class AppState:
    input_mode: Literal["single", "batch"] = "single"
    input_path: Path | None = None
    output_dir: Path | None = None
    media_info: MediaInfo | None = None
    runtime_health: RuntimeHealth | None = None
    current_task: TaskRecord | None = None
    batch_input_paths: list[Path] = field(default_factory=list)
    is_batch_running: bool = False
    batch_cancel_requested: bool = False
    batch_total_items: int = 0
    batch_current_index: int = 0
    logs: list[str] = field(default_factory=list)
    error_message: str | None = None

    def can_start(self) -> bool:
        if self.input_mode == "batch":
            has_input = bool(self.batch_input_paths)
        else:
            has_input = bool(self.input_path and self.input_path.exists())
        if not has_input:
            return False
        if self.current_task and self.current_task.status is TaskStatus.running:
            return False
        return bool(self.runtime_health and self.runtime_health.ok)

    def set_media_info(self, raw: dict[str, Any], duration_seconds: float | None) -> None:
        self.media_info = MediaInfo(raw=raw, duration_seconds=duration_seconds)
