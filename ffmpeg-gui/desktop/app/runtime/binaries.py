from __future__ import annotations

import os
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
    if _executable_path(binary) is not None:
        return True
    return shutil.which(binary) is not None


def resolve_binary_path(binary: str) -> str | None:
    executable = _executable_path(binary)
    if executable is not None:
        return str(executable)
    return shutil.which(binary)


def runtime_health_snapshot(ffmpeg_bin: str, ffprobe_bin: str, *, ffmpeg_version: str | None = None) -> RuntimeHealth:
    ffmpeg_available = binary_available(ffmpeg_bin)
    ffprobe_available = binary_available(ffprobe_bin)
    return RuntimeHealth(
        ok=ffmpeg_available and ffprobe_available,
        ffmpeg_available=ffmpeg_available,
        ffprobe_available=ffprobe_available,
        ffmpeg_path=resolve_binary_path(ffmpeg_bin),
        ffprobe_path=resolve_binary_path(ffprobe_bin),
        ffmpeg_version=ffmpeg_version,
    )


def _executable_path(binary: str) -> Path | None:
    path = Path(binary).expanduser()
    if path.is_file() and os.access(path, os.X_OK):
        return path
    return None
