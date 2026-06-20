from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from shared.contracts import MediaInfo

from .binaries import binary_available


def probe_media(ffprobe_bin: str, input_path: Path, *, timeout_seconds: int = 30) -> MediaInfo:
    if not binary_available(ffprobe_bin):
        return MediaInfo(raw={"error": "ffprobe is not available"})
    if not input_path.exists():
        return MediaInfo(raw={"error": "input file does not exist"})

    try:
        proc = subprocess.run(
            [
                ffprobe_bin,
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(input_path),
            ],
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return MediaInfo(raw={"error": str(exc)})

    if proc.returncode != 0:
        return MediaInfo(raw={"error": proc.stderr.strip() or "ffprobe failed"})

    try:
        raw: dict[str, Any] = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return MediaInfo(raw={"error": "ffprobe returned invalid JSON"})
    return MediaInfo(raw=raw, duration_seconds=media_duration_seconds(raw))


def media_duration_seconds(media_info: dict[str, Any]) -> float | None:
    value = media_info.get("format", {}).get("duration")
    try:
        duration = float(value)
    except (TypeError, ValueError):
        return None
    return duration if duration > 0 else None
