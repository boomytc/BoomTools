from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeHealth:
    ok: bool
    ffmpeg_available: bool
    ffprobe_available: bool
    ffmpeg_path: str | None
    ffprobe_path: str | None
    ffmpeg_version: str | None = None


def binary_available(binary: str) -> bool:
    if Path(binary).is_file():
        return True
    return shutil.which(binary) is not None


def resolve_binary_path(binary: str) -> str | None:
    if Path(binary).is_file():
        return str(Path(binary))
    return shutil.which(binary)
