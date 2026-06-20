from __future__ import annotations

import shlex
from collections.abc import Set as AbstractSet
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from desktop.app.ui.widgets.operation_specs import FIELD_SPECS, RAW_PRESET_OPTIONS
from desktop.app.ui.widgets.path_picker import PathPicker
from shared.contracts import MediaInfo, OPERATION_LABELS, Operation


class OperationFormWidget(QWidget):
    file_browse_requested = Signal(str, str)
    spec_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._controls: dict[str, QWidget] = {}
        self._operation_buttons: dict[Operation, QPushButton] = {}
        self._selected_operation = Operation.convert
        self._form_enabled = True
        self._batch_mode = False
        self._batch_supported_operations: set[Operation] = set()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        operation_group = QGroupBox("操作")
        operation_layout = QVBoxLayout(operation_group)
        operation_layout.setSpacing(10)
        self.operation_hint = QLabel("选择一个处理动作，然后在下方确认参数。")
        self.operation_hint.setObjectName("mutedLabel")
        operation_layout.addWidget(self.operation_hint)

        self.operation_button_group = QButtonGroup(self)
        self.operation_button_group.setExclusive(True)
        operation_grid = QGridLayout()
        operation_grid.setHorizontalSpacing(8)
        operation_grid.setVerticalSpacing(8)
        for index, operation in enumerate(OPERATION_LABELS):
            button = QPushButton(_operation_card_text(operation))
            button.setCheckable(True)
            button.setProperty("role", "operationCard")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip(OPERATION_LABELS[operation])
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.setMinimumHeight(62)
            button.clicked.connect(lambda _checked=False, op=operation: self._select_operation(op))
            self.operation_button_group.addButton(button)
            self._operation_buttons[operation] = button
            operation_grid.addWidget(button, index // 4, index % 4)
        operation_layout.addLayout(operation_grid)
        layout.addWidget(operation_group)

        common_group = QGroupBox("通用裁剪时间")
        common_layout = QFormLayout(common_group)
        self.start_seconds_edit = QLineEdit()
        self.start_seconds_edit.setPlaceholderText("可选，开始秒数")
        self.end_seconds_edit = QLineEdit()
        self.end_seconds_edit.setPlaceholderText("可选，结束秒数")
        self.start_seconds_edit.textChanged.connect(lambda _text: self.spec_changed.emit())
        self.end_seconds_edit.textChanged.connect(lambda _text: self.spec_changed.emit())
        common_layout.addRow("开始", self.start_seconds_edit)
        common_layout.addRow("结束", self.end_seconds_edit)
        layout.addWidget(common_group)

        self.fields_group = QGroupBox("参数")
        self.fields_layout = QFormLayout(self.fields_group)
        layout.addWidget(self.fields_group)
        layout.addStretch(1)

        self._select_operation(self._selected_operation, emit=False)

    def selected_operation(self) -> Operation:
        return self._selected_operation

    def set_enabled(self, enabled: bool) -> None:
        self._form_enabled = enabled
        self._sync_operation_button_states()
        self.start_seconds_edit.setEnabled(enabled)
        self.end_seconds_edit.setEnabled(enabled)
        self.fields_group.setEnabled(enabled)

    def set_batch_operation_support(self, enabled: bool, supported_operations: AbstractSet[Operation]) -> None:
        self._batch_mode = enabled
        self._batch_supported_operations = set(supported_operations)
        if self._batch_mode and self._selected_operation not in self._batch_supported_operations:
            replacement = self._first_available_operation()
            if replacement is not None:
                self._select_operation(replacement)
        self._sync_operation_hint()
        self._sync_operation_button_states()

    def set_file_path(self, field_name: str, path: str) -> None:
        widget = self._controls.get(field_name)
        if isinstance(widget, QLineEdit):
            widget.setText(path)
        elif isinstance(widget, PathPicker):
            widget.set_text(path)

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
            name = str(spec["name"])
            widget = self._create_widget(spec)
            control = self._controls.get(name, widget)
            self._controls.setdefault(name, widget)
            self.fields_layout.addRow(str(spec["label"]), widget)
            self._connect_change_signal(control)

    def _clear_fields(self) -> None:
        self._controls.clear()
        while self.fields_layout.count():
            item = self.fields_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

    def _select_operation(self, operation: Operation, *, emit: bool = True) -> None:
        if self._batch_mode and operation not in self._batch_supported_operations:
            return
        if operation == self._selected_operation and self._controls:
            return
        self._selected_operation = operation
        for candidate, button in self._operation_buttons.items():
            button.setChecked(candidate == operation)
        self._render_fields()
        if emit:
            self.spec_changed.emit()
        self._sync_operation_button_states()

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
            return self._create_file_widget(spec)
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
            combo.currentTextChanged.connect(lambda _text: self._apply_raw_preset(str(combo.currentData())))
            return combo
        return QLabel(f"Unsupported field: {kind}")

    def _create_file_widget(self, spec: dict[str, Any]) -> QWidget:
        filter_text = str(spec.get("filter", "所有文件 (*.*)"))
        field_name = str(spec["name"])
        picker = PathPicker(placeholder=str(spec.get("placeholder", "")), button_text="选择")
        picker.browse_requested.connect(lambda: self.file_browse_requested.emit(field_name, filter_text))
        self._controls[field_name] = picker
        return picker

    def _apply_raw_preset(self, args: str) -> None:
        editor = self._controls.get("raw_args")
        if not isinstance(editor, QPlainTextEdit):
            return
        editor.setPlainText(args)

    def _connect_change_signal(self, widget: QWidget) -> None:
        if isinstance(widget, QLineEdit):
            widget.textChanged.connect(lambda _text: self.spec_changed.emit())
        elif isinstance(widget, PathPicker):
            widget.text_changed.connect(lambda _text: self.spec_changed.emit())
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

    def _first_available_operation(self) -> Operation | None:
        for operation in OPERATION_LABELS:
            if not self._batch_mode or operation in self._batch_supported_operations:
                return operation
        return None

    def _sync_operation_hint(self) -> None:
        if self._batch_mode:
            self.operation_hint.setText("批量模式仅启用可对多个文件重复执行的动作。")
            return
        self.operation_hint.setText("选择一个处理动作，然后在下方确认参数。")

    def _sync_operation_button_states(self) -> None:
        for operation, button in self._operation_buttons.items():
            available = self._operation_is_available(operation)
            button.setEnabled(available)
            button.setToolTip(self._operation_tooltip(operation))

    def _operation_is_available(self, operation: Operation) -> bool:
        if not self._form_enabled:
            return False
        if self._batch_mode and operation not in self._batch_supported_operations:
            return False
        return True

    def _operation_tooltip(self, operation: Operation) -> str:
        label = OPERATION_LABELS[operation]
        if self._batch_mode and operation not in self._batch_supported_operations:
            return f"{label}\n批量模式暂不支持此动作。"
        return label


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


_OPERATION_SHORT_LABELS: dict[Operation, str] = {
    Operation.convert: "转换格式",
    Operation.resize_compress: "缩放压缩",
    Operation.compress: "压缩视频",
    Operation.extract_audio: "抽取音频",
    Operation.gif: "生成 GIF",
    Operation.mute: "静音",
    Operation.rotate: "旋转翻转",
    Operation.crop: "裁剪",
    Operation.thumbnail: "提取封面",
    Operation.reverse: "倒放",
    Operation.fade: "淡入淡出",
    Operation.adjust: "画面调整",
    Operation.loop: "循环",
    Operation.strip_metadata: "移除元数据",
    Operation.pad: "画布补边",
    Operation.denoise: "去噪",
    Operation.boomerang: "倒放回放",
    Operation.sharpen_blur: "锐化模糊",
    Operation.speed: "速度调整",
    Operation.volume: "音量调整",
    Operation.normalize_audio: "响度标准化",
    Operation.subtitles: "嵌入字幕",
    Operation.media_info: "媒体探测",
    Operation.raw: "Raw 参数",
    Operation.overlay: "叠加",
    Operation.mix_audio: "混音",
    Operation.concat: "视频拼接",
    Operation.side_by_side: "并排对比",
    Operation.picture_in_picture: "画中画",
}


def _operation_card_text(operation: Operation) -> str:
    label = OPERATION_LABELS[operation]
    category, _, fallback_title = label.partition(" - ")
    title = _OPERATION_SHORT_LABELS.get(operation, fallback_title or label)
    return f"{title}\n{category}"
