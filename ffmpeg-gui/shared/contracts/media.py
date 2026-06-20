from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MediaInfo:
    raw: dict[str, Any] = field(default_factory=dict)
    duration_seconds: float | None = None

    @property
    def has_error(self) -> bool:
        return "error" in self.raw

    @property
    def error_message(self) -> str | None:
        value = self.raw.get("error")
        return str(value) if value else None
