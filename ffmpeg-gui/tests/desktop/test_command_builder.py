from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from desktop.app.runtime.ffmpeg import (
    CommandError,
    build_command,
    build_media_info_command,
)
from shared.contracts import Operation


def test_convert_uses_allowlisted_format_and_argument_array() -> None:
    with TemporaryDirectory() as tmp:
        input_path = Path(tmp) / "input.mov"
        input_path.write_bytes(b"\x00")
        spec = build_command(
            ffmpeg_bin="ffmpeg",
            operation=Operation.convert,
            options={"output_format": "mp4"},
            input_path=input_path,
            output_dir=Path(tmp) / "outputs",
        )

    assert isinstance(spec.args, list)
    assert ";" not in spec.args
    assert spec.output_path.suffix == ".mp4"
    assert "-progress" in spec.args
    assert "pipe:1" in spec.args


def test_rejects_unknown_operation() -> None:
    with TemporaryDirectory() as tmp:
        input_path = Path(tmp) / "input.mp4"
        input_path.write_bytes(b"\x00")
        with pytest.raises(CommandError):
            build_command(
                ffmpeg_bin="ffmpeg",
                operation="stack",
                options={},
                input_path=input_path,
                output_dir=Path(tmp) / "outputs",
            )


def test_rejects_unknown_format() -> None:
    with TemporaryDirectory() as tmp:
        input_path = Path(tmp) / "input.mp4"
        input_path.write_bytes(b"\x00")
        with pytest.raises(CommandError):
            build_command(
                ffmpeg_bin="ffmpeg",
                operation=Operation.convert,
                options={"output_format": "exe"},
                input_path=input_path,
                output_dir=Path(tmp) / "outputs",
            )


def test_build_single_input_operations() -> None:
    with TemporaryDirectory() as tmp:
        input_path = Path(tmp) / "input.mp4"
        input_path.write_bytes(b"\x00")
        cases = [
            (Operation.convert, {"output_format": "avi"}, ".avi", "-c:v"),
            (Operation.compress, {"output_format": "webm", "crf": 28, "preset": "veryfast", "width": 320}, ".webm", "libvpx-vp9"),
            (Operation.extract_audio, {"audio_format": "ogg"}, ".ogg", "libvorbis"),
            (Operation.gif, {"fps": 8, "width": 320}, ".gif", "fps=8,scale=320:-1:flags=lanczos"),
            (Operation.mute, {"output_format": "mp4"}, ".mp4", "-an"),
            (Operation.rotate, {"mode": "hvflip", "output_format": "mp4"}, ".mp4", "hflip,vflip"),
            (Operation.crop, {"x": 0, "y": 0, "width": 320, "height": 180, "output_format": "mp4"}, ".mp4", "crop=320:180:0:0"),
            (Operation.thumbnail, {"timestamp_seconds": 0.5, "image_format": "jpg"}, ".jpg", "-frames:v"),
            (Operation.thumbnail, {"timestamp_seconds": 0.5, "image_format": "png"}, ".png", "-frames:v"),
            (Operation.speed, {"factor": 2, "output_format": "mp4"}, ".mp4", "setpts=0.5*PTS"),
            (Operation.volume, {"multiplier": 0.5, "output_format": "mp4"}, ".mp4", "volume=0.5"),
            (Operation.strip_metadata, {"output_format": "mp4"}, ".mp4", "-map_metadata"),
            (Operation.normalize_audio, {"target_lufs": "-16", "output_format": "mp4"}, ".mp4", "loudnorm=I=-16:LRA=11:TP=-1.5"),
            (Operation.resize_compress, {"output_format": "mp4", "width": 640, "height": 360}, ".mp4", "scale=640:360"),
            (Operation.reverse, {"output_format": "mp4", "include_audio": True}, ".mp4", "areverse"),
            (Operation.fade, {"output_format": "mp4", "fade_in_seconds": 0.3, "fade_out_seconds": 0.4, "duration_seconds": 2.0}, ".mp4", "afade=t=out"),
            (Operation.adjust, {"output_format": "mp4", "brightness": 0.1, "contrast": 1.2, "saturation": 2.0}, ".mp4", "eq=brightness=0.1:contrast=1.2:saturation=2"),
            (Operation.loop, {"output_format": "mkv", "plays": 3}, ".mkv", "-stream_loop"),
            (Operation.pad, {"output_format": "mp4", "aspect_ratio": "16:9", "color": "black"}, ".mp4", "pad="),
            (Operation.denoise, {"output_format": "mp4", "strength": "heavy"}, ".mp4", "hqdn3d=10:10:15:15"),
            (Operation.boomerang, {"output_format": "mp4"}, ".mp4", "concat=n=2"),
            (Operation.sharpen_blur, {"output_format": "mp4", "mode": "blur", "strength": "medium"}, ".mp4", "boxblur=4:1"),
            (Operation.extract_audio, {"audio_format": "ogg"}, ".ogg", "libvorbis"),
        ]

        for operation, options, expected_suffix, expected_arg in cases:
            spec = build_command(
                ffmpeg_bin="ffmpeg",
                operation=operation,
                options=options,
                input_path=input_path,
                output_dir=Path(tmp) / "outputs",
            )
            assert any(expected_arg in arg for arg in spec.args)
            assert spec.output_path.suffix == expected_suffix


def test_build_subtitle_operations() -> None:
    with TemporaryDirectory() as tmp:
        input_path = Path(tmp) / "input.mp4"
        input_path.write_bytes(b"\x00")
        soft_path = Path(tmp) / "cap.srt"
        soft_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")

        burn_path = Path(tmp) / "cap.ass"
        burn_path.write_text("[Script Info]\n[V4+ Styles]\n", encoding="utf-8")

        cases = [
            (Operation.subtitles, {"mode": "soft", "output_format": "mp4"}, {"subtitle": soft_path}, "-c:s"),
            (Operation.subtitles, {"mode": "burn", "output_format": "webm", "font_size": "large"}, {"subtitle": burn_path}, "subtitles='"),
        ]

        for operation, options, extra_inputs, expected_arg in cases:
            spec = build_command(
                ffmpeg_bin="ffmpeg",
                operation=operation,
                options=options,
                input_path=input_path,
                output_dir=Path(tmp) / "outputs",
                extra_inputs=extra_inputs,
            )
            assert any(expected_arg in arg for arg in spec.args)


def test_build_multi_input_operations() -> None:
    with TemporaryDirectory() as tmp:
        input_path = Path(tmp) / "input.mp4"
        input_path.write_bytes(b"\x00")
        secondary_image = Path(tmp) / "overlay.png"
        secondary_image.write_bytes(b"\x89PNG\r\n")
        secondary_audio = Path(tmp) / "music.mp3"
        secondary_audio.write_bytes(b"id3")
        secondary_video = Path(tmp) / "second.mp4"
        secondary_video.write_bytes(b"")

        cases = [
            (
                Operation.overlay,
                {"output_format": "mp4", "position": "top_left", "width_percent": 20},
                {"secondary_input": secondary_image},
                "overlay=",
            ),
            (
                Operation.mix_audio,
                {"output_format": "mp4", "original_volume": 1.0, "music_volume": 0.8},
                {"secondary_input": secondary_audio},
                "amix=duration=first",
            ),
            (
                Operation.concat,
                {"output_format": "mp4"},
                {"secondary_input": secondary_video},
                "concat=n=2:v=1:a=0",
            ),
            (
                Operation.side_by_side,
                {"output_format": "mp4", "layout": "horizontal", "common_dimension": 640},
                {"secondary_input": secondary_video},
                "hstack=inputs=2",
            ),
            (
                Operation.picture_in_picture,
                {"output_format": "mp4", "position": "bottom_left", "width_percent": 25},
                {"secondary_input": secondary_video},
                "overlay=",
            ),
        ]

        for operation, options, extra_inputs, expected_arg in cases:
            spec = build_command(
                ffmpeg_bin="ffmpeg",
                operation=operation,
                options=options,
                input_path=input_path,
                output_dir=Path(tmp) / "outputs",
                extra_inputs=extra_inputs,
            )
            assert any(expected_arg in arg for arg in spec.args)


def test_concat_can_explicitly_include_audio_filter() -> None:
    with TemporaryDirectory() as tmp:
        input_path = Path(tmp) / "input.mp4"
        input_path.write_bytes(b"\x00")
        secondary_video = Path(tmp) / "second.mp4"
        secondary_video.write_bytes(b"")

        spec = build_command(
            ffmpeg_bin="ffmpeg",
            operation=Operation.concat,
            options={"output_format": "mp4", "include_audio": True},
            input_path=input_path,
            output_dir=Path(tmp) / "outputs",
            extra_inputs={"secondary_input": secondary_video},
        )

    assert any("concat=n=2:v=1:a=1" in arg for arg in spec.args)
    assert "-map" in spec.args
    assert "[a]" in spec.args


def test_webm_audio_filter_operations_use_webm_compatible_codecs() -> None:
    with TemporaryDirectory() as tmp:
        input_path = Path(tmp) / "input.mp4"
        input_path.write_bytes(b"\x00")
        secondary_audio = Path(tmp) / "music.mp3"
        secondary_audio.write_bytes(b"id3")

        cases = [
            (Operation.volume, {"output_format": "webm", "multiplier": 0.5}, {}),
            (Operation.normalize_audio, {"output_format": "webm", "target_lufs": "-16"}, {}),
            (
                Operation.mix_audio,
                {"output_format": "webm", "original_volume": 1.0, "music_volume": 0.8},
                {"secondary_input": secondary_audio},
            ),
        ]

        for operation, options, extra_inputs in cases:
            spec = build_command(
                ffmpeg_bin="ffmpeg",
                operation=operation,
                options=options,
                input_path=input_path,
                output_dir=Path(tmp) / "outputs",
                extra_inputs=extra_inputs,
            )

            assert spec.output_path.suffix == ".webm"
            assert "libvpx-vp9" in spec.args
            assert "libopus" in spec.args


def test_build_raw_and_media_info_command() -> None:
    with TemporaryDirectory() as tmp:
        input_path = Path(tmp) / "input.mp4"
        input_path.write_bytes(b"\x00")
        secondary_path = Path(tmp) / "audio.wav"
        secondary_path.write_bytes(b"")

        raw_spec = build_command(
            ffmpeg_bin="ffmpeg",
            operation=Operation.raw,
            options={"raw_args": ["-vf", "scale=320:-2", "-c:v", "libx264", "-c:a", "aac"], "output_extension": "mp4"},
            input_path=input_path,
            output_dir=Path(tmp) / "outputs",
            extra_inputs={"secondary_input": secondary_path},
        )
        assert "scale=320:-2" in raw_spec.args
        assert raw_spec.output_path.suffix == ".mp4"


def test_build_media_info_command_uses_ffmpeg_binary() -> None:
    with TemporaryDirectory() as tmp:
        input_path = Path(tmp) / "input.mp4"
        input_path.write_bytes(b"\x00")
        info_spec = build_media_info_command(
            ffmpeg_bin="ffmpeg",
            input_path=input_path,
        )
        assert info_spec.output_path is None
        assert info_spec.args == ["ffmpeg", "-hide_banner", "-i", str(input_path), "-f", "null", "-"]


@pytest.mark.parametrize(
    (
        "operation",
        "options",
        "extra_inputs",
    ),
    [
        (Operation.resize_compress, {"output_format": "mp4"}, {}),
        (Operation.adjust, {"brightness": 0.0, "contrast": 1.0, "saturation": 4.0}, {}),
        (Operation.loop, {"output_format": "mp4", "plays": 1}, {}),
        (Operation.loop, {"output_format": "mp4", "plays": 3, "start_seconds": 1}, {}),
        (Operation.fade, {"fade_out_seconds": 0.5, "output_format": "mp4"}, {}),
        (Operation.fade, {"fade_in_seconds": 0.3, "fade_out_seconds": 0.5, "output_format": "mp4"}, {}),
        (Operation.subtitles, {"output_format": "mp4", "mode": "burn"}, {}),
        (Operation.overlay, {"output_format": "mp4"}, {"secondary_input": Path("/tmp/bad.txt")}),
        (Operation.mix_audio, {"output_format": "mp4"}, {"secondary_input": Path("/tmp/bad.txt")}),
        (Operation.concat, {"output_format": "mp4"}, {"secondary_input": Path("/tmp/bad.txt")}),
        (Operation.side_by_side, {"output_format": "mp4", "layout": "horizontal", "common_dimension": 64, "audio_source": "first"}, {"secondary_input": Path("/tmp/bad.txt")}),
        (Operation.picture_in_picture, {"output_format": "mp4", "position": "bottom_left", "width_percent": 30}, {"secondary_input": Path("/tmp/bad.txt")}),
        (Operation.raw, {"raw_args": ["-i", "other.mp4"], "output_extension": "mp4"}, {}),
        (Operation.raw, {"raw_args": ["-vf", "/tmp/out.mp4"], "output_extension": "mp4"}, {}),
        (Operation.raw, {"raw_args": ["-vf", "scale=320:-2"], "output_extension": "sh"}, {}),
    ],
)
def test_rejects_invalid_options(operation: Operation, options: dict[str, object], extra_inputs: dict[str, Path]) -> None:
    with TemporaryDirectory() as tmp:
        input_path = Path(tmp) / "input.mp4"
        input_path.write_bytes(b"\x00")
        with pytest.raises(CommandError):
            build_command(
                ffmpeg_bin="ffmpeg",
                operation=operation,
                options=options,
                input_path=input_path,
                output_dir=Path(tmp) / "outputs",
                extra_inputs=extra_inputs,
            )
