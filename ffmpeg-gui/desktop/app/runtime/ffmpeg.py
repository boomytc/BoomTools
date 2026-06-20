from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from shared.contracts import Operation


VIDEO_FORMATS = {"mp4", "webm", "mov", "mkv", "avi"}
AUDIO_FORMATS = {"mp3", "wav", "aac", "flac", "ogg"}
IMAGE_FORMATS = {"jpg", "png", "gif", "jpeg", "webp"}
RAW_OUTPUT_EXTENSIONS = VIDEO_FORMATS | AUDIO_FORMATS | IMAGE_FORMATS

SUBTITLE_FORMATS = {"mp4", "mkv"}
SUBTITLE_BURN_FORMATS = {"mp4", "webm", "mov", "mkv"}
SUBTITLE_FILE_EXTENSIONS = {".srt", ".vtt", ".ass", ".ssa"}
_SUBTITLE_BURN_SUPPORT_CACHE: dict[str, bool] = {}

IMAGE_INPUT_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO_INPUT_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".m4v", ".mpg", ".mpeg", ".wmv", ".ts", ".m2ts"}
AUDIO_INPUT_EXTENSIONS = {".mp3", ".wav", ".ogg", ".aac", ".flac", ".m4a"}

PRESETS = {
    "ultrafast",
    "superfast",
    "veryfast",
    "faster",
    "fast",
    "medium",
    "slow",
    "slower",
    "veryslow",
}
ROTATE_FILTERS = {
    "cw90": "transpose=1",
    "ccw90": "transpose=2",
    "180": "hflip,vflip",
    "hflip": "hflip",
    "vflip": "vflip",
    "hvflip": "hflip,vflip",
}
LOUDNESS_TARGETS = {"-14", "-16", "-23"}
RAW_FORBIDDEN_ARGS = {
    "-i",
    "-y",
    "-n",
    "-progress",
    "-nostats",
    "-nostdin",
    "-hide_banner",
    "-f",
    "-pix_fmt",
}
ASPECT_RATIOS = {
    "16:9": "16/9",
    "9:16": "9/16",
    "1:1": "1/1",
    "4:3": "4/3",
    "4:5": "4/5",
    "21:9": "21/9",
}

audio_sizes = {"small": 16, "medium": 22, "large": 30}
DENOISE_FILTERS = {
    "light": "hqdn3d=2:2:3:3",
    "medium": "hqdn3d=4:4:6:6",
    "heavy": "hqdn3d=10:10:15:15",
}
PILOT_POSITIONS = {
    "top_left": "10:10",
    "top_right": "main_w-overlay_w-10:10",
    "bottom_left": "10:main_h-overlay_h-10",
    "bottom_right": "main_w-overlay_w-10:main_h-overlay_h-10",
    "center": "(main_w-overlay_w)/2:(main_h-overlay_h)/2",
}


@dataclass(frozen=True)
class CommandSpec:
    args: list[str]
    output_path: Path | None
    output_name: str | None


class CommandError(ValueError):
    pass


def build_command(
    *,
    ffmpeg_bin: str,
    operation: Operation | str,
    options: dict[str, Any],
    input_path: Path,
    output_dir: Path,
    extra_inputs: dict[str, Path] | None = None,
) -> CommandSpec:
    output_dir.mkdir(parents=True, exist_ok=True)
    extra_inputs = extra_inputs or {}
    try:
        op = Operation(str(operation))
    except ValueError:
        raise CommandError(f"Unsupported operation: {operation}") from None

    normalized = dict(options or {})

    output_ext = _output_extension(op, normalized)
    output_name = _output_name(input_path, op, output_ext)
    output_path = _unique_output_path(output_dir / output_name)

    args = [
        ffmpeg_bin,
        "-hide_banner",
        "-nostdin",
        "-y",
        "-progress",
        "pipe:1",
        "-nostats",
    ]
    args.extend(_trim_input_args(op, normalized))
    args.extend(["-i", str(input_path)])
    args.extend(_operation_inputs(op, normalized, extra_inputs))
    args.extend(_operation_args(op, normalized, extra_inputs=extra_inputs, ffmpeg_bin=ffmpeg_bin))
    args.append(str(output_path))
    return CommandSpec(args=args, output_path=output_path, output_name=output_path.name)


def build_media_info_command(*, ffmpeg_bin: str, input_path: Path) -> CommandSpec:
    args = [ffmpeg_bin]
    args.extend(_media_info_args(input_path))
    return CommandSpec(args=args, output_path=None, output_name=None)


def parse_progress_line(line: str, duration_seconds: float | None) -> float | None:
    if duration_seconds is None or duration_seconds <= 0:
        return None
    key, _, value = line.partition("=")
    if key not in {"out_time_us", "out_time_ms", "out_time"}:
        return None
    if key == "out_time":
        elapsed = _parse_timestamp(value.strip())
    else:
        try:
            elapsed = float(value.strip()) / 1_000_000
        except ValueError:
            return None
    return max(0.0, min(1.0, elapsed / duration_seconds))


def _media_info_args(input_path: Path) -> list[str]:
    if not input_path.exists():
        raise CommandError("input file does not exist")
    return [
        "-hide_banner",
        "-i",
        str(input_path),
        "-f",
        "null",
        "-",
    ]


def validate_subtitles_burn_support(ffmpeg_bin: str) -> bool:
    if ffmpeg_bin in _SUBTITLE_BURN_SUPPORT_CACHE:
        return _SUBTITLE_BURN_SUPPORT_CACHE[ffmpeg_bin]

    try:
        proc = subprocess.run(
            [ffmpeg_bin, "-h", "filter=subtitles"],
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            timeout=8,
        )
    except (OSError, subprocess.TimeoutExpired):
        _SUBTITLE_BURN_SUPPORT_CACHE[ffmpeg_bin] = False
        return False

    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    supported = proc.returncode == 0 and "subtitles" in output.lower()
    _SUBTITLE_BURN_SUPPORT_CACHE[ffmpeg_bin] = supported
    return supported


def _operation_inputs(op: Operation, options: dict[str, Any], extra_inputs: dict[str, Path]) -> list[str]:
    if op is Operation.subtitles:
        subtitle = _required_path(extra_inputs, "subtitle", SUBTITLE_FILE_EXTENSIONS, "subtitle")
        return ["-i", str(subtitle)]

    if op is Operation.raw:
        secondary = extra_inputs.get("secondary_input")
        if secondary is None:
            return []
        return ["-i", str(_ensure_existing_file(secondary, "secondary_input"))]

    if op is Operation.overlay:
        second = _required_path(extra_inputs, "secondary_input", IMAGE_INPUT_EXTENSIONS, "overlay")
        return ["-i", str(second)]

    if op is Operation.mix_audio:
        second = _required_path(extra_inputs, "secondary_input", AUDIO_INPUT_EXTENSIONS, "mix_audio")
        if _as_bool(options.get("loop_music", True), "loop_music"):
            return ["-stream_loop", "-1", "-i", str(second)]
        return ["-i", str(second)]

    if op is Operation.concat:
        second = _required_path(extra_inputs, "secondary_input", VIDEO_INPUT_EXTENSIONS, "concat")
        return ["-i", str(second)]

    if op is Operation.side_by_side:
        second = _required_path(extra_inputs, "secondary_input", VIDEO_INPUT_EXTENSIONS, "side_by_side")
        return ["-i", str(second)]

    if op is Operation.picture_in_picture:
        second = _required_path(extra_inputs, "secondary_input", VIDEO_INPUT_EXTENSIONS, "picture_in_picture")
        if _as_bool(options.get("loop_overlay", True), "loop_overlay"):
            return ["-stream_loop", "-1", "-i", str(second)]
        return ["-i", str(second)]

    return []


def _operation_args(
    operation: Operation,
    options: dict[str, Any],
    *,
    extra_inputs: dict[str, Path] | None = None,
    ffmpeg_bin: str | None = None,
) -> list[str]:
    extra_inputs = extra_inputs or {}

    if operation is Operation.convert:
        fmt = _choice(options.get("output_format", "mp4"), VIDEO_FORMATS, "output_format")
        return _video_codec_args(fmt)

    if operation is Operation.resize_compress:
        fmt = _choice(options.get("output_format", "mp4"), VIDEO_FORMATS, "output_format")
        width = _optional_int(options.get("width"), "width")
        height = _optional_int(options.get("height"), "height")
        if width is None and height is None:
            raise CommandError("resize_compress needs at least width or height")
        width = _bounded_int(width, "width", 64, 7680) if width is not None else None
        height = _bounded_int(height, "height", 64, 4320) if height is not None else None
        crf = _bounded_int(options.get("crf", 23), "crf", 18, 51)
        preset = _choice(options.get("preset", "medium"), PRESETS, "preset")
        if width is None:
            scale = f"scale=-2:{height}"
        elif height is None:
            scale = f"scale={width}:-2"
        else:
            scale = f"scale={width}:{height}"
        return [
            "-vf",
            scale,
            "-c:v",
            "libx264",
            "-preset",
            preset,
            "-crf",
            str(crf),
            "-c:a",
            "aac",
        ]

    if operation is Operation.compress:
        fmt = _choice(options.get("output_format", "mp4"), VIDEO_FORMATS, "output_format")
        crf = _bounded_int(options.get("crf", 23), "crf", 18, 51)
        preset = _choice(options.get("preset", "medium"), PRESETS, "preset")
        width = _optional_int(options.get("width"), "width")
        if width is not None:
            width = _bounded_int(width, "width", 64, 7680)
        args: list[str] = []
        if width is not None:
            args.extend(["-vf", f"scale={width}:-2"])
        if fmt == "webm":
            args.extend(["-c:v", "libvpx-vp9", "-crf", str(crf), "-b:v", "0", "-c:a", "libopus"])
        else:
            args.extend(["-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-c:a", "aac"])
            if fmt == "mp4":
                args.extend(["-movflags", "+faststart"])
        return args

    if operation is Operation.extract_audio:
        fmt = _choice(options.get("audio_format", "mp3"), AUDIO_FORMATS, "audio_format")
        return _audio_codec_args(fmt)

    if operation is Operation.gif:
        fps = _bounded_int(options.get("fps", 10), "fps", 1, 30)
        width = _bounded_int(options.get("width", 480), "width", 64, 1920)
        return ["-vf", f"fps={fps},scale={width}:-1:flags=lanczos", "-loop", "0"]

    if operation is Operation.mute:
        fmt = _choice(options.get("output_format", "mp4"), VIDEO_FORMATS, "output_format")
        return ["-c:a", "copy", "-an"] if fmt == "webm" else _video_codec_args(fmt, include_audio=False)

    if operation is Operation.rotate:
        fmt = _choice(options.get("output_format", "mp4"), VIDEO_FORMATS, "output_format")
        mode = _choice(options.get("mode", "cw90"), set(ROTATE_FILTERS), "mode")
        return ["-vf", ROTATE_FILTERS[mode], *_video_codec_args(fmt)]

    if operation is Operation.crop:
        fmt = _choice(options.get("output_format", "mp4"), VIDEO_FORMATS, "output_format")
        x = _bounded_int(options.get("x"), "x", 0, 7680)
        y = _bounded_int(options.get("y"), "y", 0, 4320)
        width = _bounded_int(options.get("width"), "width", 1, 7680)
        height = _bounded_int(options.get("height"), "height", 1, 4320)
        return ["-vf", f"crop={width}:{height}:{x}:{y}", *_video_codec_args(fmt)]

    if operation is Operation.thumbnail:
        timestamp = _bounded_float(options.get("timestamp_seconds", 0), "timestamp_seconds", 0, 86400)
        image_format = _choice(options.get("image_format", "jpg"), {"jpg", "png"}, "image_format")
        args = ["-ss", _format_number(timestamp), "-frames:v", "1", "-an"]
        if image_format == "jpg":
            args.extend(["-q:v", "2"])
        return args

    if operation is Operation.speed:
        fmt = _choice(options.get("output_format", "mp4"), VIDEO_FORMATS, "output_format")
        factor = _bounded_float(options.get("factor", 1), "factor", 0.25, 4.0)
        return [
            "-vf",
            f"setpts={_format_number(1 / factor)}*PTS",
            "-af",
            _atempo_filter(factor),
            *_video_codec_args(fmt),
        ]

    if operation is Operation.reverse:
        fmt = _choice(options.get("output_format", "mp4"), VIDEO_FORMATS, "output_format")
        include_audio = _as_bool(options.get("include_audio", True), "include_audio")
        if include_audio:
            return ["-vf", "reverse", "-af", "areverse", *_video_codec_args(fmt)]
        return ["-vf", "reverse", *_video_codec_args(fmt, include_audio=False)]

    if operation is Operation.fade:
        fmt = _choice(options.get("output_format", "mp4"), VIDEO_FORMATS, "output_format")
        fade_in = _bounded_float(options.get("fade_in_seconds", 0), "fade_in_seconds", 0, 120.0)
        fade_out = _bounded_float(options.get("fade_out_seconds", 0), "fade_out_seconds", 0, 120.0)
        duration = _optional_float(options.get("duration_seconds"), "duration_seconds")
        if fade_out > 0 and not duration:
            raise CommandError("fade_out_seconds requires duration_seconds")
        video_filters: list[str] = []
        audio_filters: list[str] = []
        if fade_in > 0:
            video_filters.append(f"fade=t=in:st=0:d={_format_number(fade_in)}")
            audio_filters.append(f"afade=t=in:st=0:d={_format_number(fade_in)}")
        if fade_out > 0:
            start = max(0.0, duration - fade_out)
            video_filters.append(f"fade=t=out:st={_format_number(start)}:d={_format_number(fade_out)}")
            audio_filters.append(f"afade=t=out:st={_format_number(start)}:d={_format_number(fade_out)}")
        args = []
        if video_filters:
            args.extend(["-vf", ",".join(video_filters)])
        if audio_filters:
            args.extend(["-af", ",".join(audio_filters)])
        args.extend(_video_codec_args(fmt))
        return args

    if operation is Operation.adjust:
        fmt = _choice(options.get("output_format", "mp4"), VIDEO_FORMATS, "output_format")
        brightness = _bounded_float(options.get("brightness", 0.0), "brightness", -1.0, 1.0)
        contrast = _bounded_float(options.get("contrast", 1.0), "contrast", 0.0, 2.0)
        saturation = _bounded_float(options.get("saturation", 1.0), "saturation", 0.0, 3.0)
        if _as_bool(options.get("grayscale", False), "grayscale"):
            saturation = 0.0
        return ["-vf", f"eq=brightness={_format_number(brightness)}:contrast={_format_number(contrast)}:saturation={_format_number(saturation)}", *_video_codec_args(fmt)]

    if operation is Operation.loop:
        if "start_seconds" in options or "end_seconds" in options:
            raise CommandError("loop does not support trim")
        fmt = _choice(options.get("output_format", "mp4"), {"mp4", "mkv", "mov"}, "output_format")
        _bounded_int(options.get("plays", 2), "plays", 2, 50)
        return ["-c:v", "copy", "-c:a", "copy"]

    if operation is Operation.pad:
        fmt = _choice(options.get("output_format", "mp4"), VIDEO_FORMATS, "output_format")
        aspect_ratio = _choice(options.get("aspect_ratio", "16:9"), set(ASPECT_RATIOS), "aspect_ratio")
        color = _choice(options.get("color", "black"), {"black", "white", "gray"}, "color")
        ratio = ASPECT_RATIOS[aspect_ratio]
        return [
            "-vf",
            _pad_filter_for_aspect_ratio(ratio, color),
            *_video_codec_args(fmt),
        ]

    if operation is Operation.denoise:
        fmt = _choice(options.get("output_format", "mp4"), VIDEO_FORMATS, "output_format")
        strength = _choice(options.get("strength", "light"), set(DENOISE_FILTERS), "strength")
        return ["-vf", DENOISE_FILTERS[strength], *_video_codec_args(fmt)]

    if operation is Operation.boomerang:
        fmt = _choice(options.get("output_format", "mp4"), VIDEO_FORMATS, "output_format")
        return [
            "-filter_complex",
            "[0:v]split=2[v0][v1];[v1]reverse[v2];[v0][v2]concat=n=2:v=1:a=0[vout]",
            "-map",
            "[vout]",
            "-an",
            *_video_codec_args(fmt, include_audio=False),
        ]

    if operation is Operation.sharpen_blur:
        fmt = _choice(options.get("output_format", "mp4"), VIDEO_FORMATS, "output_format")
        mode = _choice(options.get("mode", "sharpen"), {"sharpen", "blur"}, "mode")
        strength = _choice(options.get("strength", "light"), {"light", "medium", "heavy"}, "strength")
        if mode == "sharpen":
            amount = {"light": 1, "medium": 2, "heavy": 3}[strength]
            filter_expr = f"unsharp=5:5:{_format_number(0.5 + (amount - 1) * 0.5)}:5:5:0.3"
        else:
            amount = {"light": 2, "medium": 4, "heavy": 8}[strength]
            filter_expr = f"boxblur={amount}:1"
        return ["-vf", filter_expr, *_video_codec_args(fmt)]

    if operation is Operation.volume:
        fmt = _choice(options.get("output_format", "mp4"), VIDEO_FORMATS, "output_format")
        multiplier = _bounded_float(options.get("multiplier", 1), "multiplier", 0, 4)
        return ["-af", f"volume={_format_number(multiplier)}", *_audio_filter_output_args(fmt)]

    if operation is Operation.strip_metadata:
        fmt = _choice(options.get("output_format", "mp4"), VIDEO_FORMATS, "output_format")
        return ["-map_metadata", "-1", *_video_codec_args(fmt)]

    if operation is Operation.normalize_audio:
        fmt = _choice(options.get("output_format", "mp4"), VIDEO_FORMATS, "output_format")
        target = _choice(options.get("target_lufs", "-16"), LOUDNESS_TARGETS, "target_lufs")
        return ["-af", f"loudnorm=I={target}:LRA=11:TP=-1.5", *_audio_filter_output_args(fmt)]

    if operation is Operation.subtitles:
        mode = _choice(options.get("mode", "soft"), {"soft", "burn"}, "mode")
        output_format = _choice(
            options.get("output_format", "mp4"),
            SUBTITLE_FORMATS | SUBTITLE_BURN_FORMATS,
            "output_format",
        )
        if mode == "soft":
            if output_format not in SUBTITLE_FORMATS:
                raise CommandError("soft subtitles only support mp4 or mkv")
            subtitle_codec = "mov_text" if output_format == "mp4" else "copy"
            return [
                "-map",
                "0:v",
                "-map",
                "0:a?",
                "-map",
                "1:0",
                "-c:v",
                "copy",
                "-c:a",
                "copy",
                "-c:s",
                subtitle_codec,
            ]

        if output_format not in SUBTITLE_BURN_FORMATS:
            raise CommandError("burn subtitles only support mp4, webm, mov, mkv")
        size = _choice(options.get("font_size", "medium"), set(audio_sizes), "font_size")
        subtitle_path = _required_path(extra_inputs, "subtitle", SUBTITLE_FILE_EXTENSIONS, "subtitle")
        escaped = subtitle_path.as_posix().replace("\\", "/")
        return [
            "-vf",
            f"subtitles='{escaped}':force_style='FontSize={audio_sizes[size]}'",
            *_video_codec_args(output_format),
        ]

    if operation is Operation.overlay:
        fmt = _choice(options.get("output_format", "mp4"), VIDEO_FORMATS, "output_format")
        width_percent = _bounded_int(options.get("width_percent", 15), "width_percent", 1, 100)
        position = _choice(options.get("position", "bottom_right"), set(PILOT_POSITIONS), "position")
        expr = PILOT_POSITIONS[position]
        ratio = _float_ratio(width_percent)
        return [
            "-filter_complex",
            f"[1:v]scale=trunc(iw*{ratio}):trunc(ih*{ratio})[ovr];[0:v][ovr]overlay={expr}[v]",
            "-map",
            "[v]",
            "-map",
            "0:a?",
            "-c:a",
            "aac",
            *_video_codec_args(fmt),
        ]

    if operation is Operation.mix_audio:
        fmt = _choice(options.get("output_format", "mp4"), VIDEO_FORMATS, "output_format")
        original_volume = _bounded_float(options.get("original_volume", 1.0), "original_volume", 0, 2)
        music_volume = _bounded_float(options.get("music_volume", 1.0), "music_volume", 0, 2)
        return [
            "-filter_complex",
            f"[0:a]volume={_format_number(original_volume)}[a0];[1:a]volume={_format_number(music_volume)}[a1];[a0][a1]amix=duration=first[a]",
            "-map",
            "0:v?",
            "-map",
            "[a]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
        ]

    if operation is Operation.concat:
        fmt = _choice(options.get("output_format", "mp4"), VIDEO_FORMATS, "output_format")
        return [
            "-filter_complex",
            "[0:v]setpts=PTS-STARTPTS[v0];[1:v]setpts=PTS-STARTPTS[v1];[0:a]asetpts=PTS-STARTPTS[a0];[1:a]asetpts=PTS-STARTPTS[a1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]",
            "-map",
            "[v]",
            "-map",
            "[a]",
            *_video_codec_args(fmt),
        ]

    if operation is Operation.side_by_side:
        fmt = _choice(options.get("output_format", "mp4"), VIDEO_FORMATS, "output_format")
        layout = _choice(options.get("layout", "horizontal"), {"horizontal", "vertical"}, "layout")
        common_dimension = _bounded_int(options.get("common_dimension", 720), "common_dimension", 64, 4320)
        audio_source = _choice(options.get("audio_source", "first"), {"first", "second", "none"}, "audio_source")
        if layout == "horizontal":
            filter_expr = (
                "[0:v]scale={0}:-2[v0];[1:v]scale={0}:-2[v1];"
                "[v0][v1]hstack=inputs=2[v]"
            ).format(common_dimension)
        else:
            filter_expr = (
                "[0:v]scale=-2:{0}[v0];[1:v]scale=-2:{0}[v1];"
                "[v0][v1]vstack=inputs=2[v]"
            ).format(common_dimension)
        args = ["-filter_complex", filter_expr, "-map", "[v]"]
        if audio_source == "first":
            args.extend(["-map", "0:a?"])
        elif audio_source == "second":
            args.extend(["-map", "1:a?"])
        else:
            args.extend(["-an"])
        args.extend(_video_codec_args(fmt))
        return args

    if operation is Operation.picture_in_picture:
        fmt = _choice(options.get("output_format", "mp4"), VIDEO_FORMATS, "output_format")
        width_percent = _bounded_int(options.get("width_percent", 30), "width_percent", 1, 100)
        position = _choice(options.get("position", "bottom_right"), set(PILOT_POSITIONS), "position")
        expr = PILOT_POSITIONS[position]
        ratio = _float_ratio(width_percent)
        overlay_suffix = ":shortest=1" if _as_bool(options.get("loop_overlay", True), "loop_overlay") else ""
        return [
            "-filter_complex",
            f"[1:v]scale=trunc(iw*{ratio}):trunc(ih*{ratio})[ovr];[0:v][ovr]overlay={expr}{overlay_suffix}[v]",
            "-map",
            "[v]",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            *_format_specific_codec_args(fmt),
        ]

    if operation is Operation.raw:
        raw = options.get("raw_args")
        if not isinstance(raw, list) or not raw:
            raise CommandError("raw_args must be a non-empty argument array")
        args = _raw_args(raw)
        if len(args) > 80:
            raise CommandError("raw_args must contain 80 or fewer arguments")
        return args

    if operation is Operation.media_info:
        raise CommandError("media_info has no output args")

    raise CommandError(f"Unsupported operation: {operation}")


def _output_extension(operation: Operation, options: dict[str, Any]) -> str:
    if operation is Operation.thumbnail:
        return _choice(options.get("image_format", "jpg"), {"jpg", "png"}, "image_format")
    if operation in {
        Operation.convert,
        Operation.resize_compress,
        Operation.compress,
        Operation.mute,
        Operation.rotate,
        Operation.crop,
        Operation.speed,
        Operation.reverse,
        Operation.fade,
        Operation.adjust,
        Operation.loop,
        Operation.pad,
        Operation.denoise,
        Operation.boomerang,
        Operation.sharpen_blur,
        Operation.volume,
        Operation.strip_metadata,
        Operation.normalize_audio,
        Operation.subtitles,
        Operation.overlay,
        Operation.mix_audio,
        Operation.concat,
        Operation.side_by_side,
        Operation.picture_in_picture,
    }:
        return _choice(options.get("output_format", "mp4"), VIDEO_FORMATS, "output_format")
    if operation in {Operation.extract_audio, Operation.raw}:
        key = "audio_format" if operation is Operation.extract_audio else "output_extension"
        default = "mp3" if operation is Operation.extract_audio else "mp4"
        if operation is Operation.extract_audio:
            return _choice(options.get(key, default), AUDIO_FORMATS, key)
        return _choice(options.get(key, default), RAW_OUTPUT_EXTENSIONS, key)
    if operation is Operation.gif:
        return "gif"
    raise CommandError(f"Unsupported operation: {operation}")


def _trim_input_args(operation: Operation, options: dict[str, Any]) -> list[str]:
    if operation is Operation.loop and (options.get("start_seconds") is not None or options.get("end_seconds") is not None):
        raise CommandError("loop does not support trim")

    start = _optional_float(options.get("start_seconds"), "start_seconds")
    end = _optional_float(options.get("end_seconds"), "end_seconds")
    if start is not None and start < 0:
        raise CommandError("start_seconds must be >= 0")
    if end is not None and end <= 0:
        raise CommandError("end_seconds must be > 0")
    if start is not None and end is not None and end <= start:
        raise CommandError("end_seconds must be greater than start_seconds")

    args: list[str] = []
    if operation is Operation.loop:
        plays = _bounded_int(options.get("plays", 2), "plays", 2, 50)
        args.extend(["-stream_loop", str(plays - 1)])
    if start is not None:
        args.extend(["-ss", _format_number(start)])
    if end is not None:
        args.extend(["-t", _format_number(end - (start or 0))])
    return args


def _ensure_existing_file(path: Path, label: str) -> Path:
    if not path.exists():
        raise CommandError(f"{label} does not exist")
    return path


def _required_path(extra_inputs: dict[str, Path], key: str, allow_ext: set[str], label: str) -> Path:
    path = extra_inputs.get(key)
    if path is None:
        raise CommandError(f"{label} input is required")
    path = _ensure_existing_file(path, label)
    if path.suffix.lower() not in allow_ext:
        allowed = ", ".join(sorted(allow_ext))
        raise CommandError(f"{label} extension must be one of: {allowed}")
    return path


def _video_codec_args(fmt: str, *, include_audio: bool = True) -> list[str]:
    if fmt == "webm":
        args = ["-c:v", "libvpx-vp9", "-crf", "23", "-b:v", "0", "-c:a", "libopus"]
        return args
    if fmt == "mp4":
        return ["-c:v", "libx264", "-preset", "medium", "-crf", "23", "-c:a", "aac", "-movflags", "+faststart"] if include_audio else ["-c:v", "libx264", "-preset", "medium", "-crf", "23", "-an"]
    return ["-c:v", "libx264", "-preset", "medium", "-crf", "23", "-c:a", "aac"] if include_audio else ["-c:v", "libx264", "-preset", "medium", "-crf", "23", "-an"]


def _audio_filter_output_args(fmt: str) -> list[str]:
    if fmt == "webm":
        return ["-c:v", "copy", "-c:a", "libopus"]
    return ["-c:v", "copy", "-c:a", "aac"]


def _format_specific_codec_args(fmt: str) -> list[str]:
    if fmt == "webm":
        return ["-c:v", "libvpx-vp9", "-c:a", "libopus"]
    if fmt == "mp4":
        return ["-movflags", "+faststart"]
    return []


def _audio_codec_args(fmt: str) -> list[str]:
    if fmt == "mp3":
        return ["-vn", "-c:a", "libmp3lame", "-q:a", "2"]
    if fmt == "wav":
        return ["-vn", "-c:a", "pcm_s16le"]
    if fmt == "aac":
        return ["-vn", "-c:a", "aac", "-b:a", "192k"]
    if fmt == "flac":
        return ["-vn", "-c:a", "flac"]
    if fmt == "ogg":
        return ["-vn", "-c:a", "libvorbis", "-q:a", "4"]
    raise CommandError(f"Unsupported audio format: {fmt}")


def _pad_filter_for_aspect_ratio(ratio: str, color: str) -> str:
    return (
        "pad="
        "'ceil(max(iw,ih*({ratio}))/2)*2':"
        "'ceil(max(ih,iw/({ratio}))/2)*2':"
        "(ow-iw)/2:(oh-ih)/2:color={color}"
    ).format(ratio=ratio, color=color)


def _raw_args(args: list[Any]) -> list[str]:
    normalized: list[str] = []
    for item in args:
        if not isinstance(item, str):
            raise CommandError("raw_args must contain strings only")
        arg = item.strip()
        if not arg:
            raise CommandError("raw_args must not contain empty arguments")
        if arg in RAW_FORBIDDEN_ARGS:
            raise CommandError(f"raw_args must not include {arg}")
        if arg.startswith(("pipe:", "file:")):
            raise CommandError("raw_args must not include file paths or pipe/file URLs")
        if _looks_like_path(arg):
            raise CommandError("raw_args must not include file paths")
        if len(arg) > 500:
            raise CommandError("raw_args values must be 500 characters or fewer")
        normalized.append(arg)
    return normalized


def _looks_like_path(value: str) -> bool:
    return "/" in value or "\\" in value


def _choice(value: Any, allowed: set[str], name: str) -> str:
    text = str(value).strip().lower()
    if text not in allowed:
        raise CommandError(f"{name} must be one of: {', '.join(sorted(allowed))}")
    return text


def _bounded_int(value: Any, name: str, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise CommandError(f"{name} must be an integer") from None
    if parsed < minimum or parsed > maximum:
        raise CommandError(f"{name} must be between {minimum} and {maximum}")
    return parsed


def _bounded_float(value: Any, name: str, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise CommandError(f"{name} must be a number") from None
    if parsed < minimum or parsed > maximum:
        raise CommandError(f"{name} must be between {_format_number(minimum)} and {_format_number(maximum)}")
    return parsed


def _optional_int(value: Any, name: str) -> int | None:
    if value in {None, ""}:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise CommandError(f"{name} must be an integer") from None


def _optional_float(value: Any, name: str) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        raise CommandError(f"{name} must be a number") from None


def _as_bool(value: Any, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value in {0, 1}:
            return bool(value)
    if isinstance(value, str):
        low = value.strip().lower()
        if low in {"1", "true", "yes", "on"}:
            return True
        if low in {"0", "false", "no", "off"}:
            return False
    raise CommandError(f"{name} must be a boolean")


def _parse_timestamp(value: str) -> float:
    match = re.match(r"(?P<h>\d+):(?P<m>\d+):(?P<s>\d+(?:\.\d+)?)", value)
    if not match:
        return 0.0
    return int(match.group("h")) * 3600 + int(match.group("m")) * 60 + float(match.group("s"))


def _atempo_filter(factor: float) -> str:
    remaining = factor
    pieces: list[str] = []
    while remaining < 0.5:
        pieces.append("atempo=0.5")
        remaining /= 0.5
    while remaining > 2.0:
        pieces.append("atempo=2")
        remaining /= 2.0
    pieces.append(f"atempo={_format_number(remaining)}")
    return ",".join(pieces)


def _float_ratio(percent: int) -> str:
    return _format_number(percent / 100)


def _format_number(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _output_name(input_path: Path, operation: Operation, ext: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", input_path.stem).strip("._") or "media"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{stem}_{operation.value}_{timestamp}.{ext}"


def _unique_output_path(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(1, 10000):
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise CommandError("could not allocate a unique output path")
