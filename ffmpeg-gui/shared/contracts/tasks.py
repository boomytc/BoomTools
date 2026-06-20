from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any

from .operations import Operation


class TaskStatus(StrEnum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


TERMINAL_STATUSES = {TaskStatus.succeeded, TaskStatus.failed, TaskStatus.cancelled}


@dataclass(frozen=True)
class TaskRequest:
    input_path: Path
    output_dir: Path
    operation: Operation
    options: dict[str, Any] = field(default_factory=dict)
    subtitle_path: Path | None = None


@dataclass
class TaskRecord:
    operation: Operation
    input_path: Path
    output_path: Path | None = None
    status: TaskStatus = TaskStatus.pending
    progress: float | None = 0.0
    message: str = "Queued"
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES


@dataclass(frozen=True)
class TaskResult:
    output_path: Path
    output_size: int
