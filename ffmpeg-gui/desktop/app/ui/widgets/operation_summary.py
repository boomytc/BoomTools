from __future__ import annotations

from pathlib import Path

from shared.contracts import Operation, operation_short_label


StackSpec = tuple[Operation, dict[str, object], dict[str, Path]]


def format_operation_summary(
    operation: Operation,
    options: dict[str, object] | None = None,
    extra_inputs: dict[str, Path] | None = None,
    *,
    compact: bool = False,
) -> str:
    option_map = options or {}
    input_map = extra_inputs or {}
    title = operation_short_label(operation)
    details = _operation_details(operation, option_map, input_map)
    range_detail = _range_detail(option_map)
    if range_detail:
        details.append(range_detail)
    if not details:
        return title
    if compact:
        return f"{title} {details[0]}"
    return f"{title} · {' · '.join(details)}"


def format_stack_summary(stack_specs: list[StackSpec], *, compact: bool = False) -> str:
    if not stack_specs:
        return "Stack"
    steps = [
        format_operation_summary(operation, options, extra_inputs, compact=True)
        for operation, options, extra_inputs in stack_specs
    ]
    if compact:
        return f"Stack x{len(stack_specs)} · {' -> '.join(steps)}"
    return f"Stack x{len(stack_specs)} · {' -> '.join(steps)}"


def _operation_details(operation: Operation, options: dict[str, object], extra_inputs: dict[str, Path]) -> list[str]:
    if operation is Operation.convert:
        return [_upper(options.get("output_format", "mp4"))]
    if operation is Operation.resize_compress:
        return [_size(options), f"CRF {_text(options.get('crf', 23))}", _text(options.get("preset", "medium"))]
    if operation is Operation.compress:
        details = [f"CRF {_text(options.get('crf', 23))}", _text(options.get("preset", "medium"))]
        width = _optional_text(options.get("width"))
        if width:
            details.append(f"{width}px")
        details.append(_upper(options.get("output_format", "mp4")))
        return details
    if operation is Operation.extract_audio:
        return [_upper(options.get("audio_format", "mp3"))]
    if operation is Operation.gif:
        return [
            f"{_text(options.get('fps', 10))}fps",
            f"{_text(options.get('width', 480))}px",
            _text(options.get("quality", "fast")),
        ]
    if operation is Operation.mute:
        return [_upper(options.get("output_format", "mp4"))]
    if operation is Operation.rotate:
        return [_rotate_label(options.get("mode", "cw90")), _upper(options.get("output_format", "mp4"))]
    if operation is Operation.crop:
        return [
            f"{_text(options.get('width', 320))}x{_text(options.get('height', 180))}"
            f"+{_text(options.get('x', 0))}+{_text(options.get('y', 0))}",
            _upper(options.get("output_format", "mp4")),
        ]
    if operation is Operation.thumbnail:
        return [f"{_number(options.get('timestamp_seconds', 0.0))}s", _upper(options.get("image_format", "jpg"))]
    if operation is Operation.reverse:
        audio = "含音频" if bool(options.get("include_audio", True)) else "无音频"
        return [audio, _upper(options.get("output_format", "mp4"))]
    if operation is Operation.fade:
        return [
            f"入{_number(options.get('fade_in_seconds', 0.0))}s",
            f"出{_number(options.get('fade_out_seconds', 0.0))}s",
            _upper(options.get("output_format", "mp4")),
        ]
    if operation is Operation.adjust:
        return [
            f"亮{_number(options.get('brightness', 0.0))}",
            f"对{_number(options.get('contrast', 1.0))}",
            f"饱{_number(options.get('saturation', 1.0))}",
            "黑白" if bool(options.get("grayscale", False)) else "彩色",
        ]
    if operation is Operation.loop:
        return [f"{_text(options.get('plays', 2))}次", _upper(options.get("output_format", "mp4"))]
    if operation is Operation.strip_metadata:
        return [_upper(options.get("output_format", "mp4"))]
    if operation is Operation.pad:
        return [_text(options.get("aspect_ratio", "16:9")), _text(options.get("color", "black"))]
    if operation is Operation.denoise:
        return [_text(options.get("strength", "light")), _upper(options.get("output_format", "mp4"))]
    if operation is Operation.boomerang:
        return [_upper(options.get("output_format", "mp4"))]
    if operation is Operation.sharpen_blur:
        return [_mode_label(options.get("mode", "sharpen")), _text(options.get("strength", "light"))]
    if operation is Operation.speed:
        return [f"{_number(options.get('factor', 1.0))}x", _upper(options.get("output_format", "mp4"))]
    if operation is Operation.volume:
        return [f"{_number(options.get('multiplier', 1.0))}x", _upper(options.get("output_format", "mp4"))]
    if operation is Operation.normalize_audio:
        return [f"{_text(options.get('target_lufs', '-16'))} LUFS", _upper(options.get("output_format", "mp4"))]
    if operation is Operation.subtitles:
        return [
            _text(options.get("mode", "soft")),
            _path_name(extra_inputs.get("subtitle")),
            _upper(options.get("output_format", "mp4")),
        ]
    if operation is Operation.raw:
        return [_short_raw_args(options.get("raw_args")), _upper(options.get("output_extension", "mp4"))]
    if operation is Operation.overlay:
        return [
            _position_label(options.get("position", "bottom_right")),
            f"{_text(options.get('width_percent', 15))}%",
            _path_name(extra_inputs.get("secondary_input")),
        ]
    if operation is Operation.mix_audio:
        return [
            f"原{_number(options.get('original_volume', 1.0))}x",
            f"混{_number(options.get('music_volume', 1.0))}x",
            _path_name(extra_inputs.get("secondary_input")),
        ]
    if operation is Operation.concat:
        audio = "拼音频" if bool(options.get("include_audio", False)) else "无拼音频"
        return [audio, _path_name(extra_inputs.get("secondary_input"))]
    if operation is Operation.side_by_side:
        return [
            _layout_label(options.get("layout", "horizontal")),
            f"{_text(options.get('common_dimension', 720))}px",
            _path_name(extra_inputs.get("secondary_input")),
        ]
    if operation is Operation.picture_in_picture:
        return [
            _position_label(options.get("position", "bottom_right")),
            f"{_text(options.get('width_percent', 30))}%",
            _path_name(extra_inputs.get("secondary_input")),
        ]
    return []


def _range_detail(options: dict[str, object]) -> str | None:
    start = _optional_text(options.get("start_seconds"))
    end = _optional_text(options.get("end_seconds"))
    if not start and not end:
        return None
    return f"范围 {start or '开头'}-{end or '结尾'}"


def _size(options: dict[str, object]) -> str:
    width = _optional_text(options.get("width"))
    height = _optional_text(options.get("height"))
    if width and height:
        return f"{width}x{height}"
    if width:
        return f"{width}px 宽"
    if height:
        return f"{height}px 高"
    return "原尺寸"


def _short_raw_args(value: object) -> str:
    if isinstance(value, list):
        text = " ".join(str(item) for item in value)
    else:
        text = str(value or "")
    text = " ".join(text.split())
    if not text:
        return "自定义参数"
    if len(text) > 42:
        return f"{text[:39]}..."
    return text


def _path_name(path: Path | None) -> str:
    if path is None:
        return "未选文件"
    return path.name


def _rotate_label(value: object) -> str:
    return {
        "cw90": "顺90",
        "ccw90": "逆90",
        "180": "180",
        "hflip": "水平翻转",
        "vflip": "垂直翻转",
        "hvflip": "水平+垂直",
    }.get(str(value), str(value))


def _position_label(value: object) -> str:
    return {
        "bottom_right": "右下",
        "top_left": "左上",
        "top_right": "右上",
        "bottom_left": "左下",
        "center": "居中",
    }.get(str(value), str(value))


def _layout_label(value: object) -> str:
    return {"horizontal": "横向", "vertical": "纵向"}.get(str(value), str(value))


def _mode_label(value: object) -> str:
    return {"sharpen": "锐化", "blur": "模糊"}.get(str(value), str(value))


def _upper(value: object) -> str:
    return str(value or "").upper()


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _text(value: object) -> str:
    return str(value or "")


def _number(value: object) -> str:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return str(value or "")
    return f"{number:.3f}".rstrip("0").rstrip(".")
