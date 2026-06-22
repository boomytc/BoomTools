from __future__ import annotations

import math
from pathlib import Path

from shared.contracts import MediaInfo, Operation, STACK_FILTER_OPERATIONS

from .ffmpeg import (
    _as_bool,
    _atempo_filter,
    _format_number,
    _gif_frame_filter,
    _output_name,
    _unique_output_path,
    _video_codec_args,
    build_palette_gif_command,
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
    output_options: dict[str, object] | None = None,
) -> CommandSpec:
    if not stack:
        raise CommandError("stack requires at least one operation")

    output_dir.mkdir(parents=True, exist_ok=True)

    for index, (operation, _options, _extra_inputs) in enumerate(stack):
        if operation not in STACK_FILTER_OPERATIONS:
            raise CommandError(f"operation not supported in stack: {operation.value}")
        if index > 0 and ("start_seconds" in _options or "end_seconds" in _options):
            raise CommandError("trim only supported on the first stack operation")
    if media_info is not None:
        validate_stack_media_context(stack=stack, media_info=media_info, input_path=input_path)

    args = [
        ffmpeg_bin,
        "-hide_banner",
        "-nostdin",
        "-y",
        "-progress",
        "pipe:1",
        "-nostats",
    ]
    trim_args = _trim_input_args(stack[0][0], stack[0][1])
    args.extend(trim_args)
    args.extend(["-i", str(input_path)])

    filters = _collect_filter_chains(stack=stack, media_info=media_info)
    video_filters = filters["vf"]
    audio_filters = filters["af"]

    final_operation, final_options, _ = stack[-1]
    stack_output = _stack_output_options(final_options=final_options, output_options=output_options)
    if stack_output["output_format"] == "gif":
        return _build_stack_gif_command(
            ffmpeg_bin=ffmpeg_bin,
            input_path=input_path,
            output_dir=output_dir,
            final_operation=final_operation,
            base_args=args,
            trim_args=trim_args,
            video_filters=video_filters,
            output_options=stack_output,
        )

    if video_filters:
        args.extend(["-vf", ",".join(video_filters)])
    if audio_filters:
        args.extend(["-af", ",".join(audio_filters)])

    output_format = str(stack_output["output_format"])
    args.extend(_video_codec_args(output_format))

    output_name = _output_name(input_path, final_operation, output_format)
    output_path = _unique_output_path(output_dir / output_name)
    args.append(str(output_path))
    return CommandSpec(args=args, output_path=output_path, output_name=output_path.name)


def _build_stack_gif_command(
    *,
    ffmpeg_bin: str,
    input_path: Path,
    output_dir: Path,
    final_operation: Operation,
    base_args: list[str],
    trim_args: list[str],
    video_filters: list[str],
    output_options: dict[str, object],
) -> CommandSpec:
    gif_filter = _gif_frame_filter(output_options)
    frame_filter = ",".join([*video_filters, gif_filter])
    output_name = _output_name(input_path, final_operation, "gif")
    output_path = _unique_output_path(output_dir / output_name)
    quality = _choice(output_options.get("quality", "fast"), {"fast", "palette"}, "quality")
    if quality == "palette":
        return build_palette_gif_command(
            ffmpeg_bin=ffmpeg_bin,
            input_path=input_path,
            output_path=output_path,
            output_name=output_path.name,
            frame_filter=frame_filter,
            trim_args=tuple(trim_args),
        )

    args = [*base_args, "-vf", frame_filter, "-an", "-loop", "0", str(output_path)]
    return CommandSpec(args=args, output_path=output_path, output_name=output_path.name)


def _stack_output_options(
    *,
    final_options: dict[str, object],
    output_options: dict[str, object] | None,
) -> dict[str, object]:
    options = dict(output_options or {})
    output_format = _choice(
        options.get("output_format", "inherit"),
        {"inherit", "mp4", "webm", "mov", "mkv", "avi", "gif"},
        "output_format",
    )
    if output_format == "inherit":
        output_format = _choice(final_options.get("output_format", "mp4"), {"mp4", "webm", "mov", "mkv", "avi"}, "output_format")
    options["output_format"] = output_format
    return options


def validate_crop_media_context(
    *,
    options: dict[str, object],
    media_info: MediaInfo,
    input_path: Path,
) -> None:
    size = _required_video_size(media_info=media_info, input_path=input_path)
    crop = _crop_region(options)
    _validate_crop_bounds(input_path=input_path, source_size=size, crop=crop)


def validate_stack_media_context(
    *,
    stack: list[tuple[Operation, dict[str, object], dict[str, Path]]],
    media_info: MediaInfo,
    input_path: Path,
) -> None:
    if not any(operation is Operation.crop for operation, _options, _extra_inputs in stack):
        return
    size = _required_video_size(media_info=media_info, input_path=input_path)
    for operation, options, _extra_inputs in stack:
        if operation is Operation.resize_compress:
            size = _resize_output_size(size, options)
            continue
        if operation is Operation.rotate:
            size = _rotate_output_size(size, options)
            continue
        if operation is Operation.pad:
            size = _pad_output_size(size, options)
            continue
        if operation is Operation.crop:
            crop = _crop_region(options)
            _validate_crop_bounds(input_path=input_path, source_size=size, crop=crop)
            size = (crop[2], crop[3])


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


def _required_video_size(*, media_info: MediaInfo, input_path: Path) -> tuple[int, int]:
    if media_info.has_error:
        raise CommandError(media_info.error_message or "media info is unavailable")
    size = _video_size(media_info)
    if size is None:
        raise CommandError(f"{input_path.name} 无法读取视频分辨率，不能预检裁剪区域")
    return size


def _video_size(media_info: MediaInfo) -> tuple[int, int] | None:
    streams = media_info.raw.get("streams", [])
    if not isinstance(streams, list):
        return None
    for stream in streams:
        if not isinstance(stream, dict):
            continue
        if stream.get("codec_type") != "video":
            continue
        try:
            width = int(stream.get("width"))
            height = int(stream.get("height"))
        except (TypeError, ValueError):
            return None
        if width > 0 and height > 0:
            return width, height
    return None


def _crop_region(options: dict[str, object]) -> tuple[int, int, int, int]:
    x = _bounded_int(options.get("x"), "x", 0, 7680)
    y = _bounded_int(options.get("y"), "y", 0, 4320)
    width = _bounded_int(options.get("width"), "width", 1, 7680)
    height = _bounded_int(options.get("height"), "height", 1, 4320)
    return x, y, width, height


def _validate_crop_bounds(
    *,
    input_path: Path,
    source_size: tuple[int, int],
    crop: tuple[int, int, int, int],
) -> None:
    source_width, source_height = source_size
    x, y, width, height = crop
    if x + width <= source_width and y + height <= source_height:
        return
    raise CommandError(
        f"裁剪区域超出文件分辨率：{input_path.name} 为 {source_width}x{source_height}，"
        f"裁剪区域 {width}x{height}+{x}+{y}"
    )


def _resize_output_size(source_size: tuple[int, int], options: dict[str, object]) -> tuple[int, int]:
    source_width, source_height = source_size
    width = _optional_int(options.get("width"), "width")
    height = _optional_int(options.get("height"), "height")
    if width is not None:
        width = _bounded_int(width, "width", 64, 7680)
    if height is not None:
        height = _bounded_int(height, "height", 64, 4320)
    if width is None and height is None:
        raise CommandError("resize_compress needs at least width or height")
    if width is None:
        width = _even_dimension(source_width * height / source_height)
    if height is None:
        height = _even_dimension(source_height * width / source_width)
    return width, height


def _rotate_output_size(source_size: tuple[int, int], options: dict[str, object]) -> tuple[int, int]:
    mode = _choice(options.get("mode", "cw90"), {"cw90", "ccw90", "180", "hflip", "vflip", "hvflip"}, "mode")
    if mode in {"cw90", "ccw90"}:
        return source_size[1], source_size[0]
    return source_size


def _pad_output_size(source_size: tuple[int, int], options: dict[str, object]) -> tuple[int, int]:
    aspect_ratio = _choice(options.get("aspect_ratio", "16:9"), {"16:9", "9:16", "1:1", "4:3", "4:5", "21:9"}, "aspect_ratio")
    source_width, source_height = source_size
    ratio_width, ratio_height = (int(part) for part in aspect_ratio.split(":", 1))
    ratio = ratio_width / ratio_height
    width = math.ceil(max(source_width, source_height * ratio) / 2) * 2
    height = math.ceil(max(source_height, source_width / ratio) / 2) * 2
    return width, height


def _even_dimension(value: float) -> int:
    return max(2, int(round(value / 2)) * 2)
