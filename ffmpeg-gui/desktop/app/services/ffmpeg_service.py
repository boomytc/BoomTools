from __future__ import annotations

import subprocess
from pathlib import Path

from desktop.app.runtime.binaries import RuntimeHealth, binary_available, resolve_binary_path
from desktop.app.runtime.ffmpeg import (
    CommandSpec,
    build_command,
    build_media_info_command,
    validate_subtitles_burn_support,
)
from desktop.app.runtime.probe import probe_media
from shared.contracts import Operation
from shared.contracts import MediaInfo, TaskRequest


class FfmpegService:
    def check_health(self, ffmpeg_bin: str, ffprobe_bin: str) -> RuntimeHealth:
        ffmpeg_available = binary_available(ffmpeg_bin)
        ffprobe_available = binary_available(ffprobe_bin)
        ffmpeg_path = resolve_binary_path(ffmpeg_bin)
        ffprobe_path = resolve_binary_path(ffprobe_bin)
        return RuntimeHealth(
            ok=ffmpeg_available and ffprobe_available,
            ffmpeg_available=ffmpeg_available,
            ffprobe_available=ffprobe_available,
            ffmpeg_path=ffmpeg_path,
            ffprobe_path=ffprobe_path,
            ffmpeg_version=self.ffmpeg_version(ffmpeg_bin) if ffmpeg_available else None,
        )

    def ffmpeg_version(self, ffmpeg_bin: str) -> str | None:
        try:
            proc = subprocess.run(
                [ffmpeg_bin, "-version"],
                capture_output=True,
                check=False,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if proc.returncode != 0:
            return None
        lines = proc.stdout.splitlines()
        return lines[0] if lines else None

    def probe(self, ffprobe_bin: str, input_path: Path) -> MediaInfo:
        return probe_media(ffprobe_bin, input_path)

    def build_command(self, ffmpeg_bin: str, request: TaskRequest) -> CommandSpec:
        if request.operation is Operation.media_info:
            return build_media_info_command(ffmpeg_bin=ffmpeg_bin, input_path=request.input_path)
        if request.operation is Operation.subtitles and str(request.options.get("mode", "soft")).strip().lower() == "burn":
            if not validate_subtitles_burn_support(ffmpeg_bin):
                raise ValueError(
                    "当前 ffmpeg 不支持 subtitles 过滤器，hard-burn 字幕需要带 libass 的构建。请安装或切换到 soft 字幕。"
                )
        return build_command(
            ffmpeg_bin=ffmpeg_bin,
            operation=request.operation,
            options=request.options,
            input_path=request.input_path,
            output_dir=request.output_dir,
            extra_inputs=request.extra_inputs,
        )
