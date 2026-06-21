from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .paths import OUTPUTS_DIR


@dataclass(frozen=True)
class AppConfig:
    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"
    output_dir: Path = OUTPUTS_DIR
    prevent_sleep_during_tasks: bool = True

    @classmethod
    def defaults(cls) -> "AppConfig":
        return cls(
            ffmpeg_bin=os.environ.get("FFMPEG_BIN", "ffmpeg"),
            ffprobe_bin=os.environ.get("FFPROBE_BIN", "ffprobe"),
            output_dir=OUTPUTS_DIR,
            prevent_sleep_during_tasks=True,
        )
