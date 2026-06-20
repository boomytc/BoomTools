from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Operation(StrEnum):
    convert = "convert"
    compress = "compress"
    extract_audio = "extract_audio"
    gif = "gif"
    mute = "mute"
    rotate = "rotate"
    crop = "crop"
    thumbnail = "thumbnail"
    speed = "speed"
    volume = "volume"
    strip_metadata = "strip_metadata"
    normalize_audio = "normalize_audio"
    subtitles = "subtitles"
    raw = "raw"


class JobStatus(StrEnum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class HealthResponse(BaseModel):
    ok: bool
    ffmpeg_available: bool
    ffprobe_available: bool
    ffmpeg_path: str | None = None
    ffmpeg_version: str | None = None


class UploadResponse(BaseModel):
    file_id: str
    original_name: str
    size: int
    media_info: dict[str, Any]


class AssetUploadResponse(BaseModel):
    asset_id: str
    kind: str
    original_name: str
    size: int


class JobCreateRequest(BaseModel):
    file_id: str = Field(min_length=1)
    operation: Operation
    options: dict[str, Any] = Field(default_factory=dict)


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    operation: Operation
    progress: float | None
    message: str
    logs_tail: list[str]
    output_name: str | None = None
    output_size: int | None = None
    download_url: str | None = None
