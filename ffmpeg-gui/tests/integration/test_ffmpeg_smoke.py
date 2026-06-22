from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from desktop.app.runtime.ffmpeg import CommandSpec, build_command
from desktop.app.runtime.filter_chain import build_stack_command
from shared.contracts import MediaInfo, Operation


def _ffmpeg_run(args: list[str]) -> None:
    proc = subprocess.run(args, check=True, capture_output=True)
    assert proc.returncode == 0


def _run_command_spec(spec: CommandSpec) -> None:
    for args in spec.setup_args:
        _ffmpeg_run(list(args))
    _ffmpeg_run(spec.args)


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

    secondary_audio = tmp_path / "music.mp3"
    secondary_video = tmp_path / "second.mp4"
    secondary_image = tmp_path / "overlay.png"
    no_audio_first = tmp_path / "no_audio_first.mp4"
    no_audio_second = tmp_path / "no_audio_second.mp4"
    raw_secondary = tmp_path / "raw.wav"

    _ffmpeg_run(
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
        ]
    )
    _ffmpeg_run(
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
            "sine=frequency=880:sample_rate=48000",
            "-t",
            "2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(secondary_video),
        ]
    )
    for no_audio_path in (no_audio_first, no_audio_second):
        _ffmpeg_run(
            [
                ffmpeg,
                "-hide_banner",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc2=size=160x90:rate=24",
                "-t",
                "1",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(no_audio_path),
            ]
        )
    _ffmpeg_run(
        [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2",
            "-c:a",
            "libmp3lame",
            str(secondary_audio),
        ]
    )
    _ffmpeg_run([
        ffmpeg,
        "-hide_banner",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=red:size=64x64",
        "-frames:v",
        "1",
        str(secondary_image),
    ])
    shutil.copy(str(input_path), raw_secondary)

    cases = [
        (Operation.convert, {"output_format": "mp4"}, {}),
        (Operation.compress, {"output_format": "mp4", "crf": 28, "preset": "veryfast", "width": 160}, {}),
        (Operation.extract_audio, {"audio_format": "mp3"}, {}),
        (Operation.gif, {"fps": 5, "width": 160}, {}),
        (Operation.mute, {"output_format": "mp4"}, {}),
        (Operation.rotate, {"mode": "cw90", "output_format": "mp4"}, {}),
        (Operation.crop, {"x": 0, "y": 0, "width": 160, "height": 120, "output_format": "mp4"}, {}),
        (Operation.thumbnail, {"timestamp_seconds": 0.5, "image_format": "jpg"}, {}),
        (Operation.speed, {"factor": 1.5, "output_format": "mp4"}, {}),
        (Operation.volume, {"multiplier": 0.5, "output_format": "mp4"}, {}),
        (Operation.strip_metadata, {"output_format": "mp4"}, {}),
        (Operation.normalize_audio, {"target_lufs": "-16", "output_format": "mp4"}, {}),
        (Operation.subtitles, {"output_format": "mp4", "mode": "soft"}, {"subtitle": subtitle_path}),
        (Operation.resize_compress, {"output_format": "mp4", "width": 160, "height": 120}, {}),
        (Operation.reverse, {"output_format": "mp4", "include_audio": True}, {}),
        (Operation.fade, {"output_format": "mp4", "fade_in_seconds": 0.2, "fade_out_seconds": 0.2, "duration_seconds": 1.0}, {}),
        (Operation.adjust, {"output_format": "mp4", "brightness": 0.1, "contrast": 1.0, "saturation": 1.0}, {}),
        (Operation.loop, {"output_format": "mp4", "plays": 2}, {}),
        (Operation.pad, {"output_format": "mp4", "aspect_ratio": "16:9", "color": "black"}, {}),
        (Operation.denoise, {"output_format": "mp4", "strength": "light"}, {}),
        (Operation.boomerang, {"output_format": "mp4"}, {}),
        (Operation.sharpen_blur, {"output_format": "mp4", "mode": "sharpen", "strength": "light"}, {}),
        (Operation.overlay, {"output_format": "mp4", "position": "bottom_right", "width_percent": 15}, {"secondary_input": secondary_image}),
        (Operation.mix_audio, {"output_format": "mp4", "original_volume": 1.0, "music_volume": 1.0}, {"secondary_input": secondary_audio}),
        (Operation.concat, {"output_format": "mp4"}, {"secondary_input": secondary_video}),
        (Operation.side_by_side, {"output_format": "mp4", "layout": "horizontal", "common_dimension": 160, "audio_source": "first"}, {"secondary_input": secondary_video}),
        (Operation.picture_in_picture, {"output_format": "mp4", "position": "bottom_left", "width_percent": 30}, {"secondary_input": secondary_video}),
        (Operation.raw, {"raw_args": ["-vf", "scale=160:-2", "-c:v", "libx264", "-c:a", "aac"], "output_extension": "mp4"}, {"secondary_input": raw_secondary}),
    ]

    for operation, options, extra_inputs in cases:
        spec = build_command(
            ffmpeg_bin=ffmpeg,
            operation=operation,
            options=options,
            input_path=input_path,
            output_dir=tmp_path / operation.value,
            extra_inputs=extra_inputs,
        )
        _run_command_spec(spec)
        if spec.output_path is not None:
            assert spec.output_path.exists(), operation
            assert spec.output_path.stat().st_size > 0, operation

    targeted_cases = [
        (input_path, Operation.volume, {"output_format": "webm", "multiplier": 0.5}, {}),
        (input_path, Operation.normalize_audio, {"output_format": "webm", "target_lufs": "-16"}, {}),
        (
            input_path,
            Operation.mix_audio,
            {"output_format": "webm", "original_volume": 1.0, "music_volume": 1.0},
            {"secondary_input": secondary_audio},
        ),
        (no_audio_first, Operation.concat, {"output_format": "mp4"}, {"secondary_input": no_audio_second}),
    ]
    for case_input_path, operation, options, extra_inputs in targeted_cases:
        spec = build_command(
            ffmpeg_bin=ffmpeg,
            operation=operation,
            options=options,
            input_path=case_input_path,
            output_dir=tmp_path / f"targeted_{operation.value}",
            extra_inputs=extra_inputs,
        )
        _run_command_spec(spec)
        if spec.output_path is not None:
            assert spec.output_path.exists(), operation
            assert spec.output_path.stat().st_size > 0, operation


def test_ffmpeg_smoke_palette_gif_quality(tmp_path: Path) -> None:
    if os.environ.get("RUN_FFMPEG_GUI_SMOKE") != "1":
        pytest.skip("Set RUN_FFMPEG_GUI_SMOKE=1 to run real ffmpeg smoke tests")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg not available")

    input_path = tmp_path / "input.mp4"
    _ffmpeg_run(
        [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=160x90:rate=12",
            "-t",
            "1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(input_path),
        ]
    )
    spec = build_command(
        ffmpeg_bin=ffmpeg,
        operation=Operation.gif,
        options={"quality": "palette", "fps": 6, "width": 120, "start_seconds": 0.0, "end_seconds": 0.8},
        input_path=input_path,
        output_dir=tmp_path / "palette_gif",
    )

    try:
        _run_command_spec(spec)
        if spec.output_path is None:
            pytest.fail("GIF 命令应有明确输出文件")
        assert spec.output_path.read_bytes()[:6] in {b"GIF87a", b"GIF89a"}
        assert spec.output_path.stat().st_size > 0
        assert spec.cleanup_paths
        assert spec.cleanup_paths[0].exists()
    finally:
        for path in spec.cleanup_paths:
            path.unlink(missing_ok=True)


def test_ffmpeg_smoke_stack_chain_three_steps(tmp_path: Path) -> None:
    if os.environ.get("RUN_FFMPEG_GUI_SMOKE") != "1":
        pytest.skip("Set RUN_FFMPEG_GUI_SMOKE=1 to run real ffmpeg smoke tests")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg not available")

    input_path = tmp_path / "input.mp4"
    _ffmpeg_run(
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
        ]
    )

    stack = [
        (Operation.crop, {"x": 0, "y": 0, "width": 160, "height": 90, "output_format": "mp4"}, {}),
        (Operation.adjust, {"brightness": 0.0, "contrast": 1.1, "saturation": 1.2, "output_format": "mp4"}, {}),
        (Operation.pad, {"aspect_ratio": "16:9", "color": "black", "output_format": "mp4"}, {}),
    ]
    spec = build_stack_command(
        ffmpeg_bin=ffmpeg,
        input_path=input_path,
        output_dir=tmp_path / "stack",
        stack=stack,
        media_info=MediaInfo(
            raw={"streams": [{"codec_type": "video", "width": 320, "height": 180}]},
            duration_seconds=2.0,
        ),
    )
    _run_command_spec(spec)

    if spec.output_path is None:
        pytest.fail("Stack 命令应有明确输出文件")
    assert spec.output_path.exists()
    assert spec.output_path.stat().st_size > 0


def test_ffmpeg_smoke_stack_palette_gif_output(tmp_path: Path) -> None:
    if os.environ.get("RUN_FFMPEG_GUI_SMOKE") != "1":
        pytest.skip("Set RUN_FFMPEG_GUI_SMOKE=1 to run real ffmpeg smoke tests")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg not available")

    input_path = tmp_path / "input.mp4"
    _ffmpeg_run(
        [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=160x90:rate=12",
            "-t",
            "1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(input_path),
        ]
    )

    stack = [
        (Operation.crop, {"x": 0, "y": 0, "width": 120, "height": 80, "output_format": "mp4"}, {}),
        (Operation.adjust, {"brightness": 0.0, "contrast": 1.1, "saturation": 1.2, "output_format": "mp4"}, {}),
    ]
    spec = build_stack_command(
        ffmpeg_bin=ffmpeg,
        input_path=input_path,
        output_dir=tmp_path / "stack_gif",
        stack=stack,
        media_info=MediaInfo(
            raw={"streams": [{"codec_type": "video", "width": 160, "height": 90}]},
            duration_seconds=1.0,
        ),
        output_options={"output_format": "gif", "quality": "palette", "fps": 6, "width": 120},
    )

    try:
        _run_command_spec(spec)
        if spec.output_path is None:
            pytest.fail("Stack GIF 命令应有明确输出文件")
        assert spec.output_path.read_bytes()[:6] in {b"GIF87a", b"GIF89a"}
        assert spec.output_path.stat().st_size > 0
    finally:
        for path in spec.cleanup_paths:
            path.unlink(missing_ok=True)
