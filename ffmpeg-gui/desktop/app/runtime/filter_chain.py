from __future__ import annotations

from pathlib import Path
from typing import Any

from shared.contracts import MediaInfo, Operation, STACK_FILTER_OPERATIONS

from .ffmpeg import (
    _as_bool,
    _atempo_filter,
    _format_number,
    _output_name,
    _unique_output_path,
    _video_codec_args,
    CommandSpec,
    CommandError,
    _bounded_float,
    _bounded_int,
    _optional_int,
    _choice,
    _pad_filter_for_aspect_ratio,
    _trim_input_args,
)

def build_stack_command(
    *,
    ffmpeg_bin: str,
    input_path: Path,
    output_dir: Path,
    stack: list[tuple[Operation, dict[str, object], dict[str, Path]]],
    media_info: MediaInfo | None = None,
) -> CommandSpec:
    if not stack:
        raise CommandError("stack requires at least one operation")

    output_dir.mkdir(parents=True, exist_ok=True)

    for index, (operation, _options, _extra_inputs) in enumerate(stack):
        if operation not in STACK_FILTER_OPERATIONS:
            raise CommandError(f"operation not supported in stack: {operation.value}")
        if index > 0 and ("start_seconds" in _options or "end_seconds" in _options):
            raise CommandError("trim only supported on the first stack operation")

    args = [
        ffmpeg_bin,
        "-hide_banner",
        "-nostdin",
        "-y",
        "-progress",
        "pipe:1",
        "-nostats",
    ]
    args.extend(_trim_input_args(stack[0][0], stack[0][1]))
    args.extend(["-i", str(input_path)])

    filters = _collect_filter_chains(stack=stack, media_info=media_info)
    video_filters = filters["vf"]
    audio_filters = filters["af"]

    if video_filters:
        args.extend(["-vf", ",".join(video_filters)])
    if audio_filters:
        args.extend(["-af", ",".join(audio_filters)])

    final_operation, final_options, _ = stack[-1]
    output_format = _choice(final_options.get("output_format", "mp4"), {"mp4", "webm", "mov", "mkv", "avi"}, "output_format")
    args.extend(_video_codec_args(output_format))

    output_name = _output_name(input_path, final_operation, output_format)
    output_path = _unique_output_path(output_dir / output_name)
    args.append(str(output_path))
    return CommandSpec(args=args, output_path=output_path, output_name=output_path.name)


def _collect_filter_chains(
    *,
    stack: list[tuple[Operation, dict[str, object], dict[str, Path]]],
    media_info: MediaInfo | None,
) -> dict[str, list[str]]:
    video_filters: list[str] = []
    audio_filters: list[str] = []

    for operation, options, _extra_inputs in stack:
        video_expr, audio_expr = _build_filters_for_operation(operation=operation, options=options, media_info=media_info)
        if video_expr:
            video_filters.append(video_expr)
        if audio_expr:
            audio_filters.append(audio_expr)

    return {"vf": video_filters, "af": audio_filters}


def _build_filters_for_operation(
    *,
    operation: Operation,
    options: dict[str, object],
    media_info: MediaInfo | None,
) -> tuple[str | None, str | None]:
    if operation is Operation.resize_compress:
        width = _optional_int(options.get("width"), "width")
        height = _optional_int(options.get("height"), "height")
        if width is not None:
            width = _bounded_int(width, "width", 64, 7680)
        if height is not None:
            height = _bounded_int(height, "height", 64, 4320)
        if width is None and height is None:
            raise CommandError("resize_compress needs at least width or height")
        if width is None:
            return f"scale=-2:{height}", None
        if height is None:
            return f"scale={width}:-2", None
        return f"scale={width}:{height}", None

    if operation is Operation.crop:
        x = _bounded_int(options.get("x"), "x", 0, 7680)
        y = _bounded_int(options.get("y"), "y", 0, 4320)
        width = _bounded_int(options.get("width"), "width", 1, 7680)
        height = _bounded_int(options.get("height"), "height", 1, 4320)
        return f"crop={width}:{height}:{x}:{y}", None

    if operation is Operation.rotate:
        ROTATE_FILTERS = {
            "cw90": "transpose=1",
            "ccw90": "transpose=2",
            "180": "hflip,vflip",
            "hflip": "hflip",
            "vflip": "vflip",
            "hvflip": "hflip,vflip",
        }
        mode = _choice(options.get("mode", "cw90"), set(ROTATE_FILTERS), "mode")
        return ROTATE_FILTERS[mode], None

    if operation is Operation.adjust:
        brightness = _bounded_float(options.get("brightness", 0.0), "brightness", -1.0, 1.0)
        contrast = _bounded_float(options.get("contrast", 1.0), "contrast", 0.0, 2.0)
        saturation = _bounded_float(options.get("saturation", 1.0), "saturation", 0.0, 3.0)
        if _as_bool(options.get("grayscale", False), "grayscale"):
            saturation = 0.0
        return f"eq=brightness={_format_number(brightness)}:contrast={_format_number(contrast)}:saturation={_format_number(saturation)}", None

    if operation is Operation.denoise:
        DENOISE_FILTERS = {
            "light": "hqdn3d=2:2:3:3",
            "medium": "hqdn3d=4:4:6:6",
            "heavy": "hqdn3d=10:10:15:15",
        }
        strength = _choice(options.get("strength", "light"), set(DENOISE_FILTERS), "strength")
        return DENOISE_FILTERS[strength], None

    if operation is Operation.sharpen_blur:
        mode = _choice(options.get("mode", "sharpen"), {"sharpen", "blur"}, "mode")
        strength = _choice(options.get("strength", "light"), {"light", "medium", "heavy"}, "strength")
        if mode == "sharpen":
            amount = {"light": 1, "medium": 2, "heavy": 3}[strength]
            return f"unsharp=5:5:{_format_number(0.5 + (amount - 1) * 0.5)}:5:5:0.3", None
        amount = {"light": 2, "medium": 4, "heavy": 8}[strength]
        return f"boxblur={amount}:1", None

    if operation is Operation.pad:
        aspect_ratio = _choice(options.get("aspect_ratio", "16:9"), {"16:9", "9:16", "1:1", "4:3", "4:5", "21:9"}, "aspect_ratio")
        color = _choice(options.get("color", "black"), {"black", "white", "gray"}, "color")
        ratios = {
            "16:9": "16/9",
            "9:16": "9/16",
            "1:1": "1/1",
            "4:3": "4/3",
            "4:5": "4/5",
            "21:9": "21/9",
        }
        ratio = ratios[aspect_ratio]
        return _pad_filter_for_aspect_ratio(ratio, color), None

    if operation is Operation.volume:
        multiplier = _bounded_float(options.get("multiplier", 1), "multiplier", 0, 4)
        return None, f"volume={_format_number(multiplier)}"

    if operation is Operation.speed:
        factor = _bounded_float(options.get("factor", 1), "factor", 0.25, 4.0)
        return f"setpts={_format_number(1 / factor)}*PTS", f"{_audio_filter_expr(factor)}"

    if operation is Operation.fade:
        fade_in = _bounded_float(options.get("fade_in_seconds", 0), "fade_in_seconds", 0, 120.0)
        fade_out = _bounded_float(options.get("fade_out_seconds", 0), "fade_out_seconds", 0, 120.0)
        duration = _extract_duration(options.get("duration_seconds"), media_info)
        if fade_out > 0 and (duration is None or duration <= 0):
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
        return (",".join(video_filters) if video_filters else None, ",".join(audio_filters) if audio_filters else None)

    return None, None


def _audio_filter_expr(factor: float) -> str:
    return _atempo_filter(factor)


def _extract_duration(raw_duration: object, media_info: MediaInfo | None) -> float | None:
    if raw_duration is not None:
        try:
            return float(raw_duration) if float(raw_duration) > 0 else None
        except (TypeError, ValueError):
            return None
    return media_info.duration_seconds if media_info else None
