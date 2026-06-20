from __future__ import annotations

from pathlib import Path

import pytest

from desktop.app.services.ffmpeg_service import FfmpegService
from shared.contracts import Operation, TaskRequest


def test_build_subtitle_burn_checks_ffmpeg_filter_support(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    service = FfmpegService()
    input_path = tmp_path / "input.mp4"
    output_dir = tmp_path / "outputs"
    subtitle_path = tmp_path / "caption.srt"
    input_path.write_bytes(b"\x00")
    output_dir.mkdir()
    subtitle_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")

    monkeypatch.setattr(
        "desktop.app.services.ffmpeg_service.validate_subtitles_burn_support",
        lambda _ffmpeg_bin: True,
    )

    spec = service.build_command(
        "ffmpeg",
        TaskRequest(
            input_path=input_path,
            output_dir=output_dir,
            operation=Operation.subtitles,
            options={"mode": "burn", "output_format": "mp4", "font_size": "medium"},
            extra_inputs={"subtitle": subtitle_path},
        ),
    )

    assert "subtitles=" in " ".join(spec.args)


def test_build_subtitle_burn_reports_clear_error_if_filter_unsupported(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    service = FfmpegService()
    input_path = tmp_path / "input.mp4"
    output_dir = tmp_path / "outputs"
    subtitle_path = tmp_path / "caption.ass"
    input_path.write_bytes(b"\x00")
    output_dir.mkdir()
    subtitle_path.write_text("[Script Info]\n", encoding="utf-8")

    monkeypatch.setattr(
        "desktop.app.services.ffmpeg_service.validate_subtitles_burn_support",
        lambda _ffmpeg_bin: False,
    )

    with pytest.raises(ValueError, match="hard-burn 字幕"):
        service.build_command(
            "ffmpeg",
            TaskRequest(
                input_path=input_path,
                output_dir=output_dir,
                operation=Operation.subtitles,
                options={"mode": "burn", "output_format": "mp4", "font_size": "medium"},
                extra_inputs={"subtitle": subtitle_path},
            ),
        )
