from __future__ import annotations

import asyncio
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CONVERT_FORMATS = {"mp4", "webm", "mov", "mkv"}
AUDIO_FORMATS = {"mp3", "wav", "aac", "flac"}
IMAGE_FORMATS = {"jpg", "png"}
SUBTITLE_FORMATS = {"mp4", "mkv"}
RAW_OUTPUT_EXTENSIONS = CONVERT_FORMATS | AUDIO_FORMATS | IMAGE_FORMATS | {"gif", "avi", "ogg"}
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
}


@dataclass(frozen=True)
class CommandSpec:
    args: list[str]
    output_path: Path
    output_name: str


class CommandError(ValueError):
    pass


def binary_available(binary: str) -> bool:
    if Path(binary).is_file():
        return True
    return shutil.which(binary) is not None


async def ffmpeg_version(ffmpeg_bin: str) -> str | None:
    if not binary_available(ffmpeg_bin):
        return None
    proc = await asyncio.create_subprocess_exec(
        ffmpeg_bin,
        "-version",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    if proc.returncode != 0:
        return None
    first_line = stdout.decode("utf-8", errors="replace").splitlines()
    return first_line[0] if first_line else None


async def probe_media(ffprobe_bin: str, input_path: Path) -> dict[str, Any]:
    if not binary_available(ffprobe_bin):
        return {"error": "ffprobe is not available"}
    proc = await asyncio.create_subprocess_exec(
        ffprobe_bin,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(input_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        return {"error": stderr.decode("utf-8", errors="replace").strip() or "ffprobe failed"}
    try:
        return json.loads(stdout.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return {"error": "ffprobe returned invalid JSON"}


def media_duration_seconds(media_info: dict[str, Any]) -> float | None:
    value = media_info.get("format", {}).get("duration")
    try:
        duration = float(value)
    except (TypeError, ValueError):
        return None
    return duration if duration > 0 else None


def build_command(
    *,
    ffmpeg_bin: str,
    operation: str,
    options: dict[str, Any],
    input_path: Path,
    output_dir: Path,
    asset_path: Path | None = None,
) -> CommandSpec:
    output_dir.mkdir(parents=True, exist_ok=True)
    normalized = dict(options or {})
    output_ext = _output_extension(operation, normalized)
    output_name = f"output.{output_ext}"
    output_path = output_dir / output_name

    args = [
        ffmpeg_bin,
        "-hide_banner",
        "-nostdin",
        "-y",
        "-progress",
        "pipe:1",
        "-nostats",
    ]
    args.extend(_trim_input_args(normalized))
    args.extend(["-i", str(input_path)])
    args.extend(_operation_args(operation, normalized, asset_path))
    args.append(str(output_path))
    return CommandSpec(args=args, output_path=output_path, output_name=output_name)


def _trim_input_args(options: dict[str, Any]) -> list[str]:
    start = _optional_float(options.get("start_seconds"), "start_seconds")
    end = _optional_float(options.get("end_seconds"), "end_seconds")
    if start is not None and start < 0:
        raise CommandError("start_seconds must be >= 0")
    if end is not None and end <= 0:
        raise CommandError("end_seconds must be > 0")
    if start is not None and end is not None and end <= start:
        raise CommandError("end_seconds must be greater than start_seconds")

    args: list[str] = []
    if start is not None:
        args.extend(["-ss", _format_number(start)])
    if end is not None:
        duration = end - (start or 0)
        args.extend(["-t", _format_number(duration)])
    return args


def _operation_args(operation: str, options: dict[str, Any], asset_path: Path | None) -> list[str]:
    if operation == "convert":
        fmt = _choice(options.get("output_format", "mp4"), CONVERT_FORMATS, "output_format")
        return _video_codec_args(fmt)

    if operation == "compress":
        fmt = _choice(options.get("output_format", "mp4"), CONVERT_FORMATS, "output_format")
        crf = _bounded_int(options.get("crf", 23), "crf", 18, 51)
        preset = _choice(options.get("preset", "medium"), PRESETS, "preset")
        args: list[str] = []
        width = _optional_int(options.get("width"), "width")
        if width is not None:
            if width < 64 or width > 7680:
                raise CommandError("width must be between 64 and 7680")
            args.extend(["-vf", f"scale={width}:-2"])
        if fmt == "webm":
            args.extend(["-c:v", "libvpx-vp9", "-crf", str(crf), "-b:v", "0", "-c:a", "libopus"])
        else:
            args.extend(["-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-c:a", "aac"])
            if fmt == "mp4":
                args.extend(["-movflags", "+faststart"])
        return args

    if operation == "extract_audio":
        fmt = _choice(options.get("audio_format", "mp3"), AUDIO_FORMATS, "audio_format")
        return _audio_codec_args(fmt)

    if operation == "gif":
        fps = _bounded_int(options.get("fps", 10), "fps", 1, 30)
        width = _bounded_int(options.get("width", 480), "width", 64, 1920)
        return [
            "-vf",
            f"fps={fps},scale={width}:-1:flags=lanczos",
            "-loop",
            "0",
        ]

    if operation == "mute":
        fmt = _choice(options.get("output_format", "mp4"), CONVERT_FORMATS, "output_format")
        return _video_codec_args(fmt, include_audio=False)

    if operation == "rotate":
        fmt = _choice(options.get("output_format", "mp4"), CONVERT_FORMATS, "output_format")
        mode = _choice(options.get("mode", "cw90"), set(ROTATE_FILTERS), "mode")
        return ["-vf", ROTATE_FILTERS[mode], *_video_codec_args(fmt)]

    if operation == "crop":
        fmt = _choice(options.get("output_format", "mp4"), CONVERT_FORMATS, "output_format")
        x = _bounded_int(options.get("x"), "x", 0, 7680)
        y = _bounded_int(options.get("y"), "y", 0, 4320)
        width = _bounded_int(options.get("width"), "width", 1, 7680)
        height = _bounded_int(options.get("height"), "height", 1, 4320)
        return ["-vf", f"crop={width}:{height}:{x}:{y}", *_video_codec_args(fmt)]

    if operation == "thumbnail":
        timestamp = _bounded_float(options.get("timestamp_seconds", 0), "timestamp_seconds", 0, 86_400)
        fmt = _choice(options.get("image_format", "jpg"), IMAGE_FORMATS, "image_format")
        args = ["-ss", _format_number(timestamp), "-frames:v", "1", "-an"]
        if fmt == "jpg":
            args.extend(["-q:v", "2"])
        return args

    if operation == "speed":
        fmt = _choice(options.get("output_format", "mp4"), CONVERT_FORMATS, "output_format")
        factor = _bounded_float(options.get("factor", 1), "factor", 0.25, 4.0)
        return [
            "-vf",
            f"setpts={_format_number(1 / factor)}*PTS",
            "-af",
            _atempo_filter(factor),
            *_video_codec_args(fmt),
        ]

    if operation == "volume":
        fmt = _choice(options.get("output_format", "mp4"), CONVERT_FORMATS, "output_format")
        multiplier = _bounded_float(options.get("multiplier", 1), "multiplier", 0, 4)
        return ["-af", f"volume={_format_number(multiplier)}", *_audio_filter_output_args(fmt)]

    if operation == "strip_metadata":
        fmt = _choice(options.get("output_format", "mp4"), CONVERT_FORMATS, "output_format")
        return ["-map_metadata", "-1", *_video_codec_args(fmt)]

    if operation == "normalize_audio":
        fmt = _choice(options.get("output_format", "mp4"), CONVERT_FORMATS, "output_format")
        target = _choice(options.get("target_lufs", "-16"), LOUDNESS_TARGETS, "target_lufs")
        return ["-af", f"loudnorm=I={target}:LRA=11:TP=-1.5", *_audio_filter_output_args(fmt)]

    if operation == "subtitles":
        if not asset_path or not asset_path.exists():
            raise CommandError("subtitle asset was not found")
        fmt = _choice(options.get("output_format", "mp4"), SUBTITLE_FORMATS, "output_format")
        subtitle_codec = "mov_text" if fmt == "mp4" else "copy"
        return [
            "-i",
            str(asset_path),
            "-c:v",
            "copy",
            "-c:a",
            "copy",
            "-c:s",
            subtitle_codec,
            "-map",
            "0:v",
            "-map",
            "0:a?",
            "-map",
            "1:0",
        ]

    if operation == "raw":
        return _raw_args(options)

    raise CommandError(f"Unsupported operation: {operation}")


def _output_extension(operation: str, options: dict[str, Any]) -> str:
    if operation in {
        "convert",
        "compress",
        "mute",
        "rotate",
        "crop",
        "speed",
        "volume",
        "strip_metadata",
        "normalize_audio",
    }:
        return _choice(options.get("output_format", "mp4"), CONVERT_FORMATS, "output_format")
    if operation == "extract_audio":
        return _choice(options.get("audio_format", "mp3"), AUDIO_FORMATS, "audio_format")
    if operation == "gif":
        return "gif"
    if operation == "thumbnail":
        return _choice(options.get("image_format", "jpg"), IMAGE_FORMATS, "image_format")
    if operation == "subtitles":
        return _choice(options.get("output_format", "mp4"), SUBTITLE_FORMATS, "output_format")
    if operation == "raw":
        return _choice(options.get("output_extension", "mp4"), RAW_OUTPUT_EXTENSIONS, "output_extension")
    raise CommandError(f"Unsupported operation: {operation}")


def _video_codec_args(fmt: str, *, include_audio: bool = True) -> list[str]:
    if fmt == "webm":
        args = ["-c:v", "libvpx-vp9", "-crf", "32", "-b:v", "0"]
        args.extend(["-c:a", "libopus"] if include_audio else ["-an"])
        return args
    args = ["-c:v", "libx264", "-preset", "medium", "-crf", "23"]
    args.extend(["-c:a", "aac"] if include_audio else ["-an"])
    if fmt == "mp4":
        args.extend(["-movflags", "+faststart"])
    return args


def _audio_filter_output_args(fmt: str) -> list[str]:
    if fmt == "webm":
        return ["-c:v", "copy", "-c:a", "libopus"]
    return ["-c:v", "copy", "-c:a", "aac"]


def _audio_codec_args(fmt: str) -> list[str]:
    if fmt == "mp3":
        return ["-vn", "-c:a", "libmp3lame", "-q:a", "2"]
    if fmt == "wav":
        return ["-vn", "-c:a", "pcm_s16le"]
    if fmt == "aac":
        return ["-vn", "-c:a", "aac", "-b:a", "192k"]
    if fmt == "flac":
        return ["-vn", "-c:a", "flac"]
    raise CommandError(f"Unsupported audio format: {fmt}")


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


def _parse_timestamp(value: str) -> float:
    match = re.match(r"(?P<h>\d+):(?P<m>\d+):(?P<s>\d+(?:\.\d+)?)", value)
    if not match:
        return 0.0
    return int(match.group("h")) * 3600 + int(match.group("m")) * 60 + float(match.group("s"))


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


def _raw_args(options: dict[str, Any]) -> list[str]:
    raw = options.get("raw_args")
    if not isinstance(raw, list) or not raw:
        raise CommandError("raw_args must be a non-empty argument array")
    if len(raw) > 80:
        raise CommandError("raw_args must contain 80 or fewer arguments")

    args: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            raise CommandError("raw_args must contain strings only")
        arg = item.strip()
        if not arg:
            raise CommandError("raw_args must not contain empty arguments")
        if len(arg) > 500:
            raise CommandError("raw_args values must be 500 characters or fewer")
        if arg in RAW_FORBIDDEN_ARGS:
            raise CommandError(f"raw_args must not include {arg}")
        if arg.startswith(("pipe:", "file:")) or "/" in arg or "\\" in arg:
            raise CommandError("raw_args must not include file paths or pipe/file URLs")
        args.append(arg)
    return args


def _atempo_filter(factor: float) -> str:
    remaining = factor
    filters: list[str] = []
    while remaining < 0.5:
        filters.append("atempo=0.5")
        remaining /= 0.5
    while remaining > 2.0:
        filters.append("atempo=2")
        remaining /= 2.0
    filters.append(f"atempo={_format_number(remaining)}")
    return ",".join(filters)


def _optional_float(value: Any, name: str) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        raise CommandError(f"{name} must be a number") from None


def _format_number(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")
