from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from desktop.app.runtime.ffmpeg import CommandError, build_command
from shared.contracts import Operation


def test_convert_uses_allowlisted_format_and_argument_array() -> None:
    with TemporaryDirectory() as tmp:
        spec = build_command(
            ffmpeg_bin="ffmpeg",
            operation=Operation.convert,
            options={"output_format": "mp4"},
            input_path=Path(tmp) / "input.mov",
            output_dir=Path(tmp) / "outputs",
        )

    assert isinstance(spec.args, list)
    assert ";" not in spec.args
    assert spec.output_path.suffix == ".mp4"
    assert "-progress" in spec.args
    assert "pipe:1" in spec.args


def test_rejects_unknown_operation() -> None:
    with TemporaryDirectory() as tmp:
        with pytest.raises(CommandError):
            build_command(
                ffmpeg_bin="ffmpeg",
                operation="stack",
                options={},
                input_path=Path(tmp) / "input.mp4",
                output_dir=Path(tmp) / "outputs",
            )


def test_rejects_unknown_format() -> None:
    with TemporaryDirectory() as tmp:
        with pytest.raises(CommandError):
            build_command(
                ffmpeg_bin="ffmpeg",
                operation=Operation.convert,
                options={"output_format": "exe"},
                input_path=Path(tmp) / "input.mp4",
                output_dir=Path(tmp) / "outputs",
            )


@pytest.mark.parametrize(
    ("operation", "options", "expected_suffix", "expected_arg"),
    [
        (Operation.convert, {"output_format": "mp4"}, ".mp4", "libx264"),
        (Operation.compress, {"output_format": "mp4", "crf": 23, "preset": "medium"}, ".mp4", "-crf"),
        (Operation.extract_audio, {"audio_format": "flac"}, ".flac", "-vn"),
        (Operation.gif, {"fps": 10, "width": 480}, ".gif", "fps=10,scale=480:-1:flags=lanczos"),
        (Operation.mute, {"output_format": "mp4"}, ".mp4", "-an"),
        (Operation.rotate, {"mode": "hflip", "output_format": "mp4"}, ".mp4", "hflip"),
        (Operation.crop, {"x": 0, "y": 0, "width": 320, "height": 180, "output_format": "mp4"}, ".mp4", "crop=320:180:0:0"),
        (Operation.thumbnail, {"timestamp_seconds": 0.5, "image_format": "png"}, ".png", "-frames:v"),
        (Operation.speed, {"factor": 2, "output_format": "mp4"}, ".mp4", "setpts=0.5*PTS"),
        (Operation.volume, {"multiplier": 0.5, "output_format": "mp4"}, ".mp4", "volume=0.5"),
        (Operation.strip_metadata, {"output_format": "mp4"}, ".mp4", "-map_metadata"),
        (Operation.normalize_audio, {"target_lufs": "-16", "output_format": "mp4"}, ".mp4", "loudnorm=I=-16:LRA=11:TP=-1.5"),
        (Operation.raw, {"raw_args": ["-vf", "scale=320:-2", "-c:v", "libx264"], "output_extension": "mp4"}, ".mp4", "scale=320:-2"),
    ],
)
def test_operations_build_argument_arrays(
    operation: Operation,
    options: dict[str, object],
    expected_suffix: str,
    expected_arg: str,
) -> None:
    with TemporaryDirectory() as tmp:
        spec = build_command(
            ffmpeg_bin="ffmpeg",
            operation=operation,
            options=options,
            input_path=Path(tmp) / "input.mp4",
            output_dir=Path(tmp) / "outputs",
        )

    assert isinstance(spec.args, list)
    assert spec.output_path.suffix == expected_suffix
    assert expected_arg in spec.args


def test_subtitles_requires_existing_allowed_subtitle_file() -> None:
    with TemporaryDirectory() as tmp:
        with pytest.raises(CommandError):
            build_command(
                ffmpeg_bin="ffmpeg",
                operation=Operation.subtitles,
                options={"output_format": "mp4"},
                input_path=Path(tmp) / "input.mp4",
                output_dir=Path(tmp) / "outputs",
            )

        bad_asset = Path(tmp) / "caption.txt"
        bad_asset.write_text("bad", encoding="utf-8")
        with pytest.raises(CommandError):
            build_command(
                ffmpeg_bin="ffmpeg",
                operation=Operation.subtitles,
                options={"output_format": "mp4"},
                input_path=Path(tmp) / "input.mp4",
                output_dir=Path(tmp) / "outputs",
                asset_path=bad_asset,
            )

        asset = Path(tmp) / "caption.srt"
        asset.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")
        spec = build_command(
            ffmpeg_bin="ffmpeg",
            operation=Operation.subtitles,
            options={"output_format": "mp4"},
            input_path=Path(tmp) / "input.mp4",
            output_dir=Path(tmp) / "outputs",
            asset_path=asset,
        )

    assert spec.output_path.suffix == ".mp4"
    assert str(asset) in spec.args
    assert "mov_text" in spec.args


@pytest.mark.parametrize(
    ("operation", "options"),
    [
        (Operation.rotate, {"mode": "sideways"}),
        (Operation.crop, {"x": 0, "y": 0, "width": 0, "height": 100}),
        (Operation.speed, {"factor": 8}),
        (Operation.volume, {"multiplier": 8}),
        (Operation.normalize_audio, {"target_lufs": "-99"}),
        (Operation.raw, {"raw_args": ["-i", "other.mp4"], "output_extension": "mp4"}),
        (Operation.raw, {"raw_args": ["-vf", "scale=320:-2"], "output_extension": "sh"}),
        (Operation.raw, {"raw_args": ["-vf", "/tmp/out.mp4"], "output_extension": "mp4"}),
    ],
)
def test_rejects_invalid_options(operation: Operation, options: dict[str, object]) -> None:
    with TemporaryDirectory() as tmp:
        with pytest.raises(CommandError):
            build_command(
                ffmpeg_bin="ffmpeg",
                operation=operation,
                options=options,
                input_path=Path(tmp) / "input.mp4",
                output_dir=Path(tmp) / "outputs",
            )
