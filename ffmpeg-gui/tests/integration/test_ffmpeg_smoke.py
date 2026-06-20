from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from desktop.app.runtime.ffmpeg import build_command
from shared.contracts import Operation


def test_ffmpeg_smoke_all_operations(tmp_path: Path) -> None:
    if os.environ.get("RUN_FFMPEG_GUI_SMOKE") != "1":
        pytest.skip("Set RUN_FFMPEG_GUI_SMOKE=1 to run real ffmpeg smoke tests")
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("ffmpeg/ffprobe not available")

    input_path = tmp_path / "input.mp4"
    subtitle_path = tmp_path / "caption.srt"
    subtitle_path.write_text("1\n00:00:00,000 --> 00:00:01,500\nHello\n", encoding="utf-8")
    subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=320x180:rate=24",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=1000:sample_rate=48000",
            "-t",
            "2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(input_path),
        ],
        check=True,
        capture_output=True,
    )

    cases = [
        (Operation.convert, {"output_format": "mp4"}, None),
        (Operation.compress, {"output_format": "mp4", "crf": 28, "preset": "veryfast", "width": 160}, None),
        (Operation.extract_audio, {"audio_format": "mp3"}, None),
        (Operation.gif, {"fps": 5, "width": 160}, None),
        (Operation.mute, {"output_format": "mp4"}, None),
        (Operation.rotate, {"mode": "cw90", "output_format": "mp4"}, None),
        (Operation.crop, {"x": 0, "y": 0, "width": 160, "height": 120, "output_format": "mp4"}, None),
        (Operation.thumbnail, {"timestamp_seconds": 0.5, "image_format": "jpg"}, None),
        (Operation.speed, {"factor": 1.5, "output_format": "mp4"}, None),
        (Operation.volume, {"multiplier": 0.5, "output_format": "mp4"}, None),
        (Operation.strip_metadata, {"output_format": "mp4"}, None),
        (Operation.normalize_audio, {"target_lufs": "-16", "output_format": "mp4"}, None),
        (Operation.subtitles, {"output_format": "mp4"}, subtitle_path),
        (Operation.raw, {"raw_args": ["-vf", "scale=160:-2", "-c:v", "libx264", "-c:a", "aac"], "output_extension": "mp4"}, None),
    ]

    for operation, options, asset_path in cases:
        spec = build_command(
            ffmpeg_bin=ffmpeg,
            operation=operation,
            options=options,
            input_path=input_path,
            output_dir=tmp_path / operation.value,
            asset_path=asset_path,
        )
        subprocess.run(spec.args, check=True, capture_output=True)
        assert spec.output_path.exists(), operation
        assert spec.output_path.stat().st_size > 0, operation
