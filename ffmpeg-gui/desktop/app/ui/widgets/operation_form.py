from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
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


FORMAT_CHOICES = ["mp4", "webm", "mov", "mkv"]
PRESET_CHOICES = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]
ROTATE_CHOICES = ["cw90", "ccw90", "180", "hflip", "vflip", "hvflip"]


FIELD_SPECS: dict[Operation, list[dict[str, Any]]] = {
    Operation.convert: [
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.compress: [
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": FORMAT_CHOICES, "default": "mp4"},
        {"name": "crf", "label": "CRF", "kind": "int", "min": 18, "max": 51, "default": 23},
        {"name": "preset", "label": "Preset", "kind": "choice", "choices": PRESET_CHOICES, "default": "medium"},
        {"name": "width", "label": "宽度", "kind": "optional_int", "placeholder": "可选，例如 1280"},
    ],
    Operation.extract_audio: [
        {"name": "audio_format", "label": "音频格式", "kind": "choice", "choices": ["mp3", "wav", "aac", "flac"], "default": "mp3"},
    ],
    Operation.gif: [
        {"name": "fps", "label": "帧率", "kind": "int", "min": 1, "max": 30, "default": 10},
        {"name": "width", "label": "宽度", "kind": "int", "min": 64, "max": 1920, "default": 480},
    ],
    Operation.mute: [
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.rotate: [
        {"name": "mode", "label": "模式", "kind": "choice", "choices": ROTATE_CHOICES, "default": "cw90"},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.crop: [
        {"name": "x", "label": "X", "kind": "int", "min": 0, "max": 7680, "default": 0},
        {"name": "y", "label": "Y", "kind": "int", "min": 0, "max": 4320, "default": 0},
        {"name": "width", "label": "宽度", "kind": "int", "min": 1, "max": 7680, "default": 320},
        {"name": "height", "label": "高度", "kind": "int", "min": 1, "max": 4320, "default": 180},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.thumbnail: [
        {"name": "timestamp_seconds", "label": "时间点秒", "kind": "float", "min": 0.0, "max": 86400.0, "default": 0.0},
        {"name": "image_format", "label": "图片格式", "kind": "choice", "choices": ["jpg", "png"], "default": "jpg"},
    ],
    Operation.speed: [
        {"name": "factor", "label": "倍率", "kind": "float", "min": 0.25, "max": 4.0, "default": 1.0},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.volume: [
        {"name": "multiplier", "label": "音量倍数", "kind": "float", "min": 0.0, "max": 4.0, "default": 1.0},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.strip_metadata: [
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.normalize_audio: [
        {"name": "target_lufs", "label": "目标 LUFS", "kind": "choice", "choices": ["-14", "-16", "-23"], "default": "-16"},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": FORMAT_CHOICES, "default": "mp4"},
    ],
    Operation.subtitles: [
        {"name": "subtitle_path", "label": "字幕文件", "kind": "file", "placeholder": ".srt / .vtt / .ass / .ssa"},
        {"name": "output_format", "label": "输出格式", "kind": "choice", "choices": ["mp4", "mkv"], "default": "mp4"},
    ],
    Operation.raw: [
        {"name": "raw_args", "label": "参数数组", "kind": "raw", "placeholder": "-vf scale=1280:-2 -c:v libx264"},
        {"name": "output_extension", "label": "输出扩展名", "kind": "choice", "choices": ["mp4", "webm", "mov", "mkv", "mp3", "wav", "aac", "flac", "jpg", "png", "gif", "avi", "ogg"], "default": "mp4"},
    ],
}


class OperationFormWidget(QWidget):
    subtitle_browse_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._controls: dict[str, QWidget] = {}
        self._subtitle_line: QLineEdit | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        operation_group = QGroupBox("操作")
        operation_layout = QVBoxLayout(operation_group)
        self.operation_combo = QComboBox()
        for operation, label in OPERATION_LABELS.items():
            self.operation_combo.addItem(label, operation.value)
        self.operation_combo.currentIndexChanged.connect(self._render_fields)
        operation_layout.addWidget(self.operation_combo)
        layout.addWidget(operation_group)

        common_group = QGroupBox("通用裁剪时间")
        common_layout = QFormLayout(common_group)
        self.start_seconds_edit = QLineEdit()
        self.start_seconds_edit.setPlaceholderText("可选，开始秒数")
        self.end_seconds_edit = QLineEdit()
        self.end_seconds_edit.setPlaceholderText("可选，结束秒数")
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

    def set_subtitle_path(self, path: str) -> None:
        if self._subtitle_line is not None:
            self._subtitle_line.setText(path)

    def collect(self) -> tuple[Operation, dict[str, Any], Path | None]:
        operation = self.selected_operation()
        options: dict[str, Any] = {}
        subtitle_path: Path | None = None

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
            elif kind == "optional_int":
                text = widget.text().strip()  # type: ignore[attr-defined]
                if text:
                    options[name] = int(text)
            elif kind == "file":
                text = widget.text().strip()  # type: ignore[attr-defined]
                if text:
                    subtitle_path = Path(text)
            elif kind == "raw":
                text = widget.toPlainText().strip()  # type: ignore[attr-defined]
                if not text:
                    raise ValueError("Raw 参数不能为空")
                try:
                    options[name] = shlex.split(text)
                except ValueError as exc:
                    raise ValueError(f"Raw 参数解析失败: {exc}") from exc
        return operation, options, subtitle_path

    def _render_fields(self) -> None:
        self._clear_fields()
        self._subtitle_line = None
        operation = self.selected_operation()
        for spec in FIELD_SPECS[operation]:
            widget = self._create_widget(spec)
            name = str(spec["name"])
            if name not in self._controls:
                self._controls[name] = widget
            self.fields_layout.addRow(str(spec["label"]), widget)

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
            button = QPushButton("选择")
            button.clicked.connect(self.subtitle_browse_requested.emit)
            layout.addWidget(line, 1)
            layout.addWidget(button)
            self._subtitle_line = line
            self._controls[str(spec["name"])] = line
            return container
        if kind == "raw":
            editor = QPlainTextEdit()
            editor.setPlaceholderText(str(spec.get("placeholder", "")))
            editor.setFixedHeight(96)
            editor.setToolTip("仅填写 ffmpeg 输入文件之后、输出文件之前的参数；不要包含 -i、输入路径或输出路径。")
            return editor
        return QLabel(f"Unsupported field: {kind}")


def _parse_float_text(text: str, label: str) -> float:
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"{label}必须是数字") from exc
