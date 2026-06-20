from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    ffmpeg_missing = "FFMPEG_MISSING"
    ffprobe_missing = "FFPROBE_MISSING"
    invalid_input = "INVALID_INPUT"
    invalid_operation = "INVALID_OPERATION"
    command_failed = "COMMAND_FAILED"
    task_cancelled = "TASK_CANCELLED"


@dataclass(frozen=True)
class AppError:
    code: ErrorCode
    message: str
    detail: dict[str, Any] = field(default_factory=dict)
