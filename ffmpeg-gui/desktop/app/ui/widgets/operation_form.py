from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from shared.contracts import OPERATION_LABELS, Operation

VIDEO_FORMAT_CHOICES = ["mp4", "webm", "mov", "mkv", "avi"]
AUDIO_FORMAT_CHOICES = ["mp3", "wav", "aac", "flac", "ogg"]
ROTATE_CHOICES = ["cw90", "ccw90", "180", "hflip", "vflip", "hvflip"]
RAW_PRESET_OPTIONS: list[tuple[str, str]] = [
    ("drawbox watermark", "-vf drawbox=x=40:y=40:w=160:h=80:color=black@0.5:t=4"),
    ("cap framerate", "-r 30"),
    ("grayscale", "-vf hue=s=0"),
    ("loudnorm", "-af loudnorm"),
    ("lossless remux", "-c copy"),
    ("letterbox", "-vf pad=ih*16/9:ih:(ow-iw)/2:(oh-ih)/2:color=black"),
    ("denoise", "-vf hqdn3d=2:2:3:3"),
    ("sharpen", "-vf unsharp=5:5:1.0:5:5:0.3"),
    ("deshake", "-vf deshake"),
    ("vignette", "-vf vignette=PI/4"),
    ("extract wav", "-vn -acodec pcm_s16le"),
    ("first frame", "-vframes 1 -q:v 2"),
    ("replace audio with second input", "-map 0:v -map 1:a -c:v copy -c:a copy -shortest"),
]

FIELD_SPECS: dict[Operation, list[dict[str, Any]]] = {
    Operation.convert: [
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.resize_compress: [
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
        {"name": "width", "label": "宽度", "kind": "optional_int", "placeholder": "可选，例如 1280"},
        {"name": "height", "label": "高度", "kind": "optional_int", "placeholder": "可选，例如 720"},
        {"name": "crf", "label": "CRF", "kind": "int", "min": 18, "max": 51, "default": 23},
        {"name": "preset", "label": "Preset", "kind": "choice", "choices": [
            "ultrafast",
            "superfast",
            "veryfast",
            "faster",
            "fast",
            "medium",
            "slow",
            "slower",
            "veryslow",
        ], "default": "medium"},
    ],
    Operation.compress: [
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
        {"name": "crf", "label": "CRF", "kind": "int", "min": 18, "max": 51, "default": 23},
        {"name": "preset", "label": "Preset", "kind": "choice", "choices": [
            "ultrafast",
            "superfast",
            "veryfast",
            "faster",
            "fast",
            "medium",
            "slow",
            "slower",
            "veryslow",
        ], "default": "medium"},
        {"name": "width", "label": "宽度", "kind": "optional_int", "placeholder": "可选，例如 1280"},
    ],
    Operation.extract_audio: [
        {"name": "audio_format", "label": "音频格式", "kind": "choice", "choices": AUDIO_FORMAT_CHOICES, "default": "mp3"},
    ],
    Operation.gif: [
        {"name": "fps", "label": "帧率", "kind": "int", "min": 1, "max": 30, "default": 10},
        {"name": "width", "label": "宽度", "kind": "int", "min": 64, "max": 1920, "default": 480},
    ],
    Operation.mute: [
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.rotate: [
        {"name": "mode", "label": "模式", "kind": "choice", "choices": ROTATE_CHOICES, "default": "cw90"},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.crop: [
        {"name": "x", "label": "X", "kind": "int", "min": 0, "max": 7680, "default": 0},
        {"name": "y", "label": "Y", "kind": "int", "min": 0, "max": 4320, "default": 0},
        {"name": "width", "label": "宽度", "kind": "int", "min": 1, "max": 7680, "default": 320},
        {"name": "height", "label": "高度", "kind": "int", "min": 1, "max": 4320, "default": 180},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.thumbnail: [
        {"name": "timestamp_seconds", "label": "时间点秒", "kind": "float", "min": 0.0, "max": 86400.0, "default": 0.0},
        {"name": "image_format", "label": "图片格式", "kind": "choice", "choices": ["jpg", "png"], "default": "jpg"},
    ],
    Operation.speed: [
        {"name": "factor", "label": "倍率", "kind": "float", "min": 0.25, "max": 4.0, "default": 1.0},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.reverse: [
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
        {"name": "include_audio", "label": "保留音频", "kind": "bool", "default": True},
    ],
    Operation.fade: [
        {"name": "fade_in_seconds", "label": "淡入秒数", "kind": "float", "min": 0.0, "max": 120.0, "default": 0.0},
        {"name": "fade_out_seconds", "label": "淡出秒数", "kind": "float", "min": 0.0, "max": 120.0, "default": 0.0},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.adjust: [
        {"name": "brightness", "label": "亮度", "kind": "float", "min": -1.0, "max": 1.0, "default": 0.0},
        {"name": "contrast", "label": "对比度", "kind": "float", "min": 0.0, "max": 2.0, "default": 1.0},
        {"name": "saturation", "label": "饱和度", "kind": "float", "min": 0.0, "max": 3.0, "default": 1.0},
        {"name": "grayscale", "label": "黑白", "kind": "bool", "default": False},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.loop: [
        {"name": "plays", "label": "循环次数", "kind": "int", "min": 2, "max": 50, "default": 2},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": ["mp4", "mkv", "mov"], "default": "mp4"},
    ],
    Operation.strip_metadata: [
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.pad: [
        {"name": "aspect_ratio", "label": "目标比例", "kind": "choice", "choices": ["16:9", "9:16", "1:1", "4:3", "4:5", "21:9"], "default": "16:9"},
        {"name": "color", "label": "背景颜色", "kind": "choice", "choices": ["black", "white", "gray"], "default": "black"},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.denoise: [
        {"name": "strength", "label": "降噪强度", "kind": "choice", "choices": ["light", "medium", "heavy"], "default": "light"},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.boomerang: [
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.sharpen_blur: [
        {"name": "mode", "label": "模式", "kind": "choice", "choices": ["sharpen", "blur"], "default": "sharpen"},
        {"name": "strength", "label": "强度", "kind": "choice", "choices": ["light", "medium", "heavy"], "default": "light"},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.volume: [
        {"name": "multiplier", "label": "音量倍数", "kind": "float", "min": 0.0, "max": 4.0, "default": 1.0},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.normalize_audio: [
        {"name": "target_lufs", "label": "目标 LUFS", "kind": "choice", "choices": ["-14", "-16", "-23"], "default": "-16"},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.subtitles: [
        {"name": "subtitle", "label": "字幕文件", "kind": "file", "extensions": ["*.srt", "*.vtt", "*.ass", "*.ssa"], "filter": "Subtitles (*.srt *.vtt *.ass *.ssa)", "placeholder": "请先选择字幕文件"},
        {"name": "mode", "label": "字幕模式", "kind": "choice", "choices": ["soft", "burn"], "default": "soft"},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": ["mp4", "webm", "mov", "mkv"], "default": "mp4"},
        {"name": "font_size", "label": "文字大小", "kind": "choice", "choices": ["small", "medium", "large"], "default": "medium"},
    ],
    Operation.media_info: [],
    Operation.raw: [
        {"name": "raw_preset", "label": "示例命令", "kind": "raw_preset"},
        {"name": "raw_args", "label": "参数数组", "kind": "raw", "placeholder": "仅填写 ffmpeg 输入文件之后、输出文件之前的参数；不要包含 -i、输入路径或输出路径。"},
        {"name": "secondary_input", "label": "第二输入（可选）", "kind": "file", "filter": "媒体文件 (*.*)", "placeholder": "可选，用于复杂组合"},
        {"name": "output_extension", "label": "输出扩展名", "kind": "choice", "choices": ["mp4", "webm", "mov", "mkv", "avi", "mp3", "wav", "aac", "flac", "ogg", "jpg", "png", "gif"], "default": "mp4"},
    ],
    Operation.overlay: [
        {"name": "secondary_input", "label": "叠加图片", "kind": "file", "extensions": ["*.png", "*.jpg", "*.jpeg", "*.webp", "*.gif"], "filter": "Images (*.png *.jpg *.jpeg *.webp *.gif)"},
        {"name": "position", "label": "位置", "kind": "choice", "choices": ["bottom_right", "top_left", "top_right", "bottom_left", "center"], "default": "bottom_right"},
        {"name": "width_percent", "label": "缩放百分比", "kind": "int", "min": 1, "max": 100, "default": 15},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.mix_audio: [
        {"name": "secondary_input", "label": "音频文件", "kind": "file", "extensions": ["*.mp3", "*.wav", "*.ogg", "*.aac", "*.flac", "*.m4a"], "filter": "Audio (*.mp3 *.wav *.ogg *.aac *.flac *.m4a)"},
        {"name": "original_volume", "label": "原音量", "kind": "float", "min": 0.0, "max": 2.0, "default": 1.0},
        {"name": "music_volume", "label": "混音音量", "kind": "float", "min": 0.0, "max": 2.0, "default": 1.0},
        {"name": "loop_music", "label": "循环音乐", "kind": "bool", "default": True},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.concat: [
        {"name": "secondary_input", "label": "第二段视频", "kind": "file", "extensions": [
            "*.mp4",
            "*.mov",
            "*.mkv",
            "*.avi",
            "*.webm",
            "*.flv",
            "*.m4v",
            "*.mpg",
            "*.mpeg",
            "*.wmv",
            "*.ts",
            "*.m2ts",
        ], "filter": "Videos (*.mp4 *.mov *.mkv *.avi *.webm *.flv *.m4v *.mpg *.mpeg *.wmv *.ts *.m2ts)"},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.side_by_side: [
        {"name": "secondary_input", "label": "第二段视频", "kind": "file", "extensions": [
            "*.mp4",
            "*.mov",
            "*.mkv",
            "*.avi",
            "*.webm",
            "*.flv",
            "*.m4v",
            "*.mpg",
            "*.mpeg",
            "*.wmv",
            "*.ts",
            "*.m2ts",
        ], "filter": "Videos (*.mp4 *.mov *.mkv *.avi *.webm *.flv *.m4v *.mpg *.mpeg *.wmv *.ts *.m2ts)"},
        {"name": "layout", "label": "布局", "kind": "choice", "choices": ["horizontal", "vertical"], "default": "horizontal"},
        {"name": "common_dimension", "label": "统一尺寸", "kind": "int", "min": 64, "max": 4320, "default": 720},
        {"name": "audio_source", "label": "音频来源", "kind": "choice", "choices": ["first", "second", "none"], "default": "first"},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.picture_in_picture: [
        {"name": "secondary_input", "label": "覆盖画面", "kind": "file", "extensions": [
            "*.mp4",
            "*.mov",
            "*.mkv",
            "*.avi",
            "*.webm",
            "*.flv",
            "*.m4v",
            "*.mpg",
            "*.mpeg",
            "*.wmv",
            "*.ts",
            "*.m2ts",
        ], "filter": "Videos (*.mp4 *.mov *.mkv *.avi *.webm *.flv *.m4v *.mpg *.mpeg *.wmv *.ts *.m2ts)"},
        {"name": "position", "label": "位置", "kind": "choice", "choices": ["bottom_right", "top_left", "top_right", "bottom_left", "center"], "default": "bottom_right"},
        {"name": "width_percent", "label": "缩放百分比", "kind": "int", "min": 1, "max": 100, "default": 30},
        {"name": "loop_overlay", "label": "循环覆盖视频", "kind": "bool", "default": True},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": VIDEO_FORMAT_CHOICES, "default": "mp4"},
    ],
}


class OperationFormWidget(QWidget):
    file_browse_requested = Signal(str, str)
    spec_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._controls: dict[str, QWidget] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        operation_group = QGroupBox("操作")
        operation_layout = QVBoxLayout(operation_group)
        self.operation_combo = QComboBox()
        for operation, label in OPERATION_LABELS.items():
            self.operation_combo.addItem(label, operation.value)
        self.operation_combo.currentIndexChanged.connect(self._render_fields)
        self.operation_combo.currentIndexChanged.connect(self.spec_changed.emit)
        operation_layout.addWidget(self.operation_combo)
        layout.addWidget(operation_group)

        common_group = QGroupBox("通用裁剪时间")
        common_layout = QFormLayout(common_group)
        self.start_seconds_edit = QLineEdit()
        self.start_seconds_edit.setPlaceholderText("可选，开始秒数")
        self.end_seconds_edit = QLineEdit()
        self.end_seconds_edit.setPlaceholderText("可选，结束秒数")
        self.start_seconds_edit.textChanged.connect(self.spec_changed.emit)
        self.end_seconds_edit.textChanged.connect(self.spec_changed.emit)
        common_layout.addRow("开始", self.start_seconds_edit)
        common_layout.addRow("结束", self.end_seconds_edit)
        layout.addWidget(common_group)

        self.fields_group = QGroupBox("参数")
        self.fields_layout = QFormLayout(self.fields_group)
        layout.addWidget(self.fields_group)
        layout.addStretch(1)

        self._render_fields()

    def selected_operation(self) -> Operation:
        return Operation(str(self.operation_combo.currentData()))

    def set_enabled(self, enabled: bool) -> None:
        self.operation_combo.setEnabled(enabled)
        self.start_seconds_edit.setEnabled(enabled)
        self.end_seconds_edit.setEnabled(enabled)
        self.fields_group.setEnabled(enabled)

    def set_file_path(self, field_name: str, path: str) -> None:
        widget = self._controls.get(field_name)
        if isinstance(widget, QLineEdit):
            widget.setText(path)

    def set_subtitle_path(self, path: str) -> None:
        self.set_file_path("subtitle", path)

    def collect(self) -> tuple[Operation, dict[str, Any], dict[str, Path]]:
        operation = self.selected_operation()
        options: dict[str, Any] = {}
        extra_inputs: dict[str, Path] = {}

        start = self.start_seconds_edit.text().strip()
        end = self.end_seconds_edit.text().strip()
        if start:
            options["start_seconds"] = _parse_float_text(start, "开始")
        if end:
            options["end_seconds"] = _parse_float_text(end, "结束")

        for spec in FIELD_SPECS[operation]:
            name = str(spec["name"])
            kind = str(spec["kind"])
            widget = self._controls[name]
            if kind == "choice":
                options[name] = str(widget.currentData())  # type: ignore[attr-defined]
            elif kind == "int":
                options[name] = int(widget.value())  # type: ignore[attr-defined]
            elif kind == "float":
                options[name] = float(widget.value())  # type: ignore[attr-defined]
            elif kind == "bool":
                options[name] = bool(widget.isChecked())  # type: ignore[attr-defined]
            elif kind == "optional_int":
                text = widget.text().strip()  # type: ignore[attr-defined]
                if text:
                    options[name] = int(text)
            elif kind == "file":
                text = widget.text().strip()  # type: ignore[attr-defined]
                if text:
                    extra_inputs[name] = Path(text)
            elif kind == "raw":
                text = widget.toPlainText().strip()  # type: ignore[attr-defined]
                if not text:
                    raise ValueError("Raw 参数不能为空")
                try:
                    options[name] = shlex.split(text)
                except ValueError as exc:
                    raise ValueError(f"Raw 参数解析失败: {exc}") from exc
            elif kind == "raw_preset":
                pass

        return operation, options, extra_inputs

    def _render_fields(self) -> None:
        self._clear_fields()
        operation = self.selected_operation()
        for spec in FIELD_SPECS.get(operation, []):
            widget = self._create_widget(spec)
            name = str(spec["name"])
            self._controls[name] = widget
            self.fields_layout.addRow(str(spec["label"]), widget)
            self._connect_change_signal(widget)

    def _clear_fields(self) -> None:
        self._controls.clear()
        while self.fields_layout.count():
            item = self.fields_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

    def _create_widget(self, spec: dict[str, Any]) -> QWidget:
        kind = str(spec["kind"])
        if kind == "choice":
            combo = QComboBox()
            for value in spec["choices"]:
                combo.addItem(str(value), str(value))
            default = str(spec.get("default", ""))
            index = combo.findData(default)
            if index >= 0:
                combo.setCurrentIndex(index)
            return combo
        if kind == "int":
            spin = QSpinBox()
            spin.setRange(int(spec["min"]), int(spec["max"]))
            spin.setValue(int(spec["default"]))
            return spin
        if kind == "float":
            spin = QDoubleSpinBox()
            spin.setRange(float(spec["min"]), float(spec["max"]))
            spin.setDecimals(3)
            spin.setSingleStep(0.1)
            spin.setValue(float(spec["default"]))
            return spin
        if kind == "bool":
            checkbox = QCheckBox()
            checkbox.setChecked(bool(spec.get("default", False)))
            return checkbox
        if kind == "optional_int":
            edit = QLineEdit()
            edit.setPlaceholderText(str(spec.get("placeholder", "")))
            return edit
        if kind == "file":
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            line = QLineEdit()
            line.setPlaceholderText(str(spec.get("placeholder", "")))
            filter_text = str(spec.get("filter", "所有文件 (*.*)"))
            button = QPushButton("选择")
            button.clicked.connect(lambda _checked=False, field_name=str(spec["name"]), file_filter=filter_text: self.file_browse_requested.emit(field_name, file_filter))
            layout.addWidget(line, 1)
            layout.addWidget(button)
            self._controls[name_from_spec(spec)] = line
            return container
        if kind == "raw":
            editor = QPlainTextEdit()
            editor.setPlaceholderText(str(spec.get("placeholder", "")))
            editor.setFixedHeight(96)
            editor.setToolTip("仅填写 ffmpeg 输入文件之后、输出文件之前的参数；不要包含 -i、输入路径或输出路径。")
            return editor
        if kind == "raw_preset":
            combo = QComboBox()
            combo.addItem("不使用示例命令", "")
            for label, args in RAW_PRESET_OPTIONS:
                combo.addItem(label, args)
            combo.currentTextChanged.connect(
                lambda _text: self._apply_raw_preset(str(combo.currentData()))
            )
            return combo
        return QLabel(f"Unsupported field: {kind}")

    def _apply_raw_preset(self, args: str) -> None:
        editor = self._controls.get("raw_args")
        if not isinstance(editor, QPlainTextEdit):
            return
        editor.setPlainText(args)

    def _connect_change_signal(self, widget: QWidget) -> None:
        if isinstance(widget, QLineEdit):
            widget.textChanged.connect(lambda _text: self.spec_changed.emit())
        elif isinstance(widget, QPlainTextEdit):
            widget.textChanged.connect(lambda: self.spec_changed.emit())
        elif isinstance(widget, QComboBox):
            widget.currentTextChanged.connect(lambda _text: self.spec_changed.emit())
        elif isinstance(widget, QSpinBox):
            widget.valueChanged.connect(lambda _value: self.spec_changed.emit())
        elif isinstance(widget, QDoubleSpinBox):
            widget.valueChanged.connect(lambda _value: self.spec_changed.emit())
        elif isinstance(widget, QCheckBox):
            widget.toggled.connect(lambda _checked: self.spec_changed.emit())

    def apply_media_defaults(self, media_info: MediaInfo) -> None:
        video_width, video_height = self._video_size(media_info.raw)
        if not video_width or not video_height:
            return

        operation = self.selected_operation()
        if operation == Operation.crop:
            self._set_line_text("x", "0")
            self._set_line_text("y", "0")
            self._set_optional_line("width", str(video_width))
            self._set_optional_line("height", str(video_height))

        if operation == Operation.resize_compress:
            self._set_optional_line("width", str(video_width))
            self._set_optional_line("height", str(video_height))

        if operation == Operation.thumbnail and media_info.duration_seconds:
            midpoint = max(media_info.duration_seconds / 2, 0.0)
            self._set_line_text("timestamp_seconds", f"{midpoint:.3f}".rstrip("0").rstrip("."))

        if operation == Operation.pad:
            ratio_combo = self._controls.get("aspect_ratio")
            if isinstance(ratio_combo, QComboBox) and ratio_combo.currentText() not in {"16:9", "9:16", "1:1", "4:3", "4:5", "21:9"}:
                ratio_combo.setCurrentText("16:9")
            color_combo = self._controls.get("color")
            if isinstance(color_combo, QComboBox) and color_combo.currentText() not in {"black", "white", "gray"}:
                color_combo.setCurrentText("black")

    def _video_size(self, raw: dict[str, Any]) -> tuple[int | None, int | None]:
        streams = raw.get("streams", [])
        for stream in streams:
            if not isinstance(stream, dict):
                continue
            if stream.get("codec_type") != "video":
                continue
            width = _to_int(stream.get("width"))
            height = _to_int(stream.get("height"))
            if width and height:
                return width, height
        return None, None

    def _set_optional_line(self, name: str, text: str) -> None:
        widget = self._controls.get(name)
        if not isinstance(widget, QLineEdit):
            return
        current = widget.text().strip()
        if current:
            return
        widget.setText(text)

    def _set_line_text(self, name: str, text: str) -> None:
        widget = self._controls.get(name)
        if not isinstance(widget, QLineEdit):
            return
        widget.setText(text)


def name_from_spec(spec: dict[str, Any]) -> str:
    return str(spec["name"])


def _to_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return parsed


def _parse_float_text(text: str, label: str) -> float:
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"{label}必须是数字") from exc
