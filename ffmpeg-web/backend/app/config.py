from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
DATA_ROOT = PROJECT_ROOT / "data"
UPLOADS_ROOT = DATA_ROOT / "uploads"
JOBS_ROOT = DATA_ROOT / "jobs"


@dataclass(frozen=True)
class ToolConfig:
    ffmpeg_bin: str
    ffprobe_bin: str
    data_root: Path = DATA_ROOT
    uploads_root: Path = UPLOADS_ROOT
    jobs_root: Path = JOBS_ROOT


def resolve_binary(env_name: str, fallback: str) -> str:
    configured = os.environ.get(env_name)
    if configured:
        return configured
    return shutil.which(fallback) or fallback


def get_config() -> ToolConfig:
    return ToolConfig(
        ffmpeg_bin=resolve_binary("FFMPEG_BIN", "ffmpeg"),
        ffprobe_bin=resolve_binary("FFPROBE_BIN", "ffprobe"),
    )


def ensure_data_dirs() -> None:
    UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
    JOBS_ROOT.mkdir(parents=True, exist_ok=True)

