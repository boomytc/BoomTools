from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QLineEdit,
    QPlainTextEdit,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from desktop.app.ui.components import FixedScrollArea, FormSection, PanelFrame
from desktop.app.ui.widgets.operation_field_factory import OperationFieldFactory, configure_parameter_field
from desktop.app.ui.widgets.operation_specs import FIELD_SPECS
from desktop.app.ui.widgets.path_picker import PathPicker
from shared.contracts import MediaInfo, Operation, operation_title_and_category


PARAMETER_CONTENT_MAX_WIDTH = 680
PARAMETER_SCROLL_RIGHT_GUTTER = 8


class OperationParameterForm(PanelFrame):
    file_browse_requested = Signal(str, str)
    spec_changed = Signal()

    def __init__(self) -> None:
        super().__init__("参数")
        self.setObjectName("parameterFrame")
        self.setMinimumWidth(320)
        self.setMinimumHeight(236)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self._controls: dict[str, QWidget] = {}
        self._operation = Operation.convert
        self._media_info: MediaInfo | None = None
        self._field_factory = OperationFieldFactory(
            file_browse_requested=lambda field_name, file_filter: self.file_browse_requested.emit(field_name, file_filter),
            raw_preset_selected=self._apply_raw_preset,
        )
        self._layout_sync_timer = QTimer(self)
        self._layout_sync_timer.setSingleShot(True)
        self._layout_sync_timer.timeout.connect(self._sync_content_minimum_height)

        self.selected_operation_label = self.description_label

        self.parameter_scroll_area = FixedScrollArea(right_gutter=PARAMETER_SCROLL_RIGHT_GUTTER)
        self.parameter_scroll_area.setObjectName("parameterScroll")
        self.parameter_scroll_area.setMinimumHeight(164)
        self.parameter_content_widget = QWidget()
        self.parameter_content_widget.setObjectName("parameterScrollContent")
        self.parameter_content_widget.setMaximumWidth(PARAMETER_CONTENT_MAX_WIDTH)
        self.parameter_content_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        parameter_content_layout = QVBoxLayout(self.parameter_content_widget)
        parameter_content_layout.setContentsMargins(2, 0, 14, 0)
        parameter_content_layout.setSpacing(6)

        self.range_section = FormSection("处理范围（可选）")
        self.start_seconds_edit = QLineEdit()
        self.start_seconds_edit.setPlaceholderText("留空则从开头开始")
        self.end_seconds_edit = QLineEdit()
        self.end_seconds_edit.setPlaceholderText("留空则处理到结尾")
        self.start_seconds_edit.setToolTip("可选。填写秒数后，从该时间点开始处理。")
        self.end_seconds_edit.setToolTip("可选。填写秒数后，在该时间点结束处理。")
        configure_parameter_field(self.start_seconds_edit)
        configure_parameter_field(self.end_seconds_edit)
        self.start_seconds_edit.textChanged.connect(lambda _text: self.spec_changed.emit())
        self.end_seconds_edit.textChanged.connect(lambda _text: self.spec_changed.emit())
        self.range_section.add_row("开始", self.start_seconds_edit)
        self.range_section.add_row("结束", self.end_seconds_edit)
        parameter_content_layout.addWidget(self.range_section)

        self.fields_section = FormSection("动作参数", empty_text="当前动作无需额外参数。")
        parameter_content_layout.addWidget(self.fields_section)
        self.parameter_scroll_area.set_content_widget(self.parameter_content_widget)
        self.body_layout().addWidget(self.parameter_scroll_area)
        self.set_operation(self._operation, emit=False)

    def controls(self) -> dict[str, QWidget]:
        return dict(self._controls)

    def set_operation(self, operation: Operation, *, emit: bool = True) -> None:
        self._operation = operation
        self._render_fields()
        if self._media_info is not None:
            self.apply_media_defaults(self._media_info)
        if emit:
            self.spec_changed.emit()

    def collect(self) -> tuple[Operation, dict[str, Any], dict[str, Path]]:
        options: dict[str, Any] = {}
        extra_inputs: dict[str, Path] = {}

        start = self.start_seconds_edit.text().strip()
        end = self.end_seconds_edit.text().strip()
        if start:
            options["start_seconds"] = _parse_float_text(start, "开始")
        if end:
            options["end_seconds"] = _parse_float_text(end, "结束")

        for spec in FIELD_SPECS[self._operation]:
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

        if self._operation is Operation.fade and self._media_info and self._media_info.duration_seconds:
            options["duration_seconds"] = self._media_info.duration_seconds

        return self._operation, options, extra_inputs

    def set_file_path(self, field_name: str, path: str) -> None:
        widget = self._controls.get(field_name)
        if isinstance(widget, QLineEdit):
            widget.setText(path)
        elif isinstance(widget, PathPicker):
            widget.set_text(path)

    def set_subtitle_path(self, path: str) -> None:
        self.set_file_path("subtitle", path)

    def set_trim_start_seconds(self, seconds: float) -> None:
        self._set_line_text("start_seconds", _format_seconds(seconds))

    def set_trim_end_seconds(self, seconds: float) -> None:
        self._set_line_text("end_seconds", _format_seconds(seconds))

    def clear_trim_range(self) -> None:
        self.start_seconds_edit.clear()
        self.end_seconds_edit.clear()

    def set_thumbnail_timestamp_seconds(self, seconds: float) -> bool:
        if self._operation is not Operation.thumbnail:
            return False
        widget = self._controls.get("timestamp_seconds")
        if widget is None:
            return False
        _set_control_text(widget, _format_seconds(seconds))
        return True

    def trim_range(self) -> tuple[float | None, float | None]:
        return _optional_float_text(self.start_seconds_edit.text()), _optional_float_text(self.end_seconds_edit.text())

    def set_payload(self, options: dict[str, object], extra_inputs: dict[str, Path]) -> None:
        self._set_line_text("start_seconds", _option_text(options.get("start_seconds")))
        self._set_line_text("end_seconds", _option_text(options.get("end_seconds")))
        for spec in FIELD_SPECS.get(self._operation, []):
            name = str(spec["name"])
            kind = str(spec["kind"])
            widget = self._controls.get(name)
            if widget is None:
                continue
            if kind == "choice" and isinstance(widget, QComboBox):
                _set_combo_value(widget, options.get(name, spec.get("default", "")))
            elif kind == "int" and isinstance(widget, QSpinBox):
                widget.setValue(int(options.get(name, spec.get("default", widget.value()))))
            elif kind == "float" and isinstance(widget, QDoubleSpinBox):
                widget.setValue(float(options.get(name, spec.get("default", widget.value()))))
            elif kind == "bool" and isinstance(widget, QCheckBox):
                widget.setChecked(bool(options.get(name, spec.get("default", False))))
            elif kind == "optional_int" and isinstance(widget, QLineEdit):
                widget.setText(_option_text(options.get(name)))
            elif kind == "file":
                input_path = extra_inputs.get(name)
                _set_path_widget_text(widget, "" if input_path is None else str(input_path))
            elif kind == "raw" and isinstance(widget, QPlainTextEdit):
                raw_args = options.get(name, [])
                if isinstance(raw_args, list):
                    widget.setPlainText(shlex.join(str(arg) for arg in raw_args))
                else:
                    widget.setPlainText(str(raw_args))
        self._sync_content_minimum_height()

    def set_enabled(self, enabled: bool) -> None:
        super().setEnabled(enabled)
        self.start_seconds_edit.setEnabled(enabled)
        self.end_seconds_edit.setEnabled(enabled)

    def apply_media_defaults(self, media_info: MediaInfo) -> None:
        self._media_info = media_info
        video_width, video_height = self._video_size(media_info.raw)
        if video_width and video_height:
            if self._operation == Operation.crop:
                self._set_line_text("x", "0")
                self._set_line_text("y", "0")
                self._set_line_text("width", str(video_width))
                self._set_line_text("height", str(video_height))

            if self._operation == Operation.resize_compress:
                self._set_optional_line("width", str(video_width))
                self._set_optional_line("height", str(video_height))

        if self._operation == Operation.thumbnail and media_info.duration_seconds:
            midpoint = max(media_info.duration_seconds / 2, 0.0)
            self._set_line_text("timestamp_seconds", f"{midpoint:.3f}".rstrip("0").rstrip("."))

        if self._operation == Operation.pad:
            ratio_combo = self._controls.get("aspect_ratio")
            if isinstance(ratio_combo, QComboBox) and ratio_combo.currentText() not in {"16:9", "9:16", "1:1", "4:3", "4:5", "21:9"}:
                ratio_combo.setCurrentText("16:9")
            color_combo = self._controls.get("color")
            if isinstance(color_combo, QComboBox) and color_combo.currentText() not in {"black", "white", "gray"}:
                color_combo.setCurrentText("black")

    def _render_fields(self) -> None:
        self._clear_fields()
        self._sync_selected_operation_label()
        has_fields = False
        for spec in FIELD_SPECS.get(self._operation, []):
            has_fields = True
            name = str(spec["name"])
            widget = self._field_factory.create_widget(spec)
            configure_parameter_field(widget)
            self._controls[name] = widget
            self.fields_section.add_row(str(spec["label"]), widget)
            self._connect_change_signal(widget)
        self.fields_section.title_label.setVisible(has_fields)
        self.fields_section.empty_label.setVisible(not has_fields)
        self._sync_content_minimum_height()
        self._layout_sync_timer.start(0)
        self.parameter_scroll_area.verticalScrollBar().setValue(0)

    def _sync_content_minimum_height(self) -> None:
        self.range_section.layout().activate()
        self.fields_section.layout().activate()
        content_layout = self.parameter_content_widget.layout()
        if content_layout is None:
            return
        content_layout.activate()
        hint_height = max(content_layout.sizeHint().height(), self.parameter_content_widget.sizeHint().height())
        self.parameter_content_widget.setMinimumHeight(hint_height)
        self.parameter_content_widget.updateGeometry()

    def _clear_fields(self) -> None:
        self._controls.clear()
        self.fields_section.clear()

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

    def _sync_selected_operation_label(self) -> None:
        title, category = operation_title_and_category(self._operation)
        self.set_description(f"{title} · {category}")

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
        if _control_has_user_value(widget):
            return
        _set_control_text(widget, text)

    def _set_line_text(self, name: str, text: str) -> None:
        if name == "start_seconds":
            widget = self.start_seconds_edit
        elif name == "end_seconds":
            widget = self.end_seconds_edit
        else:
            widget = self._controls.get(name)
        _set_control_text(widget, text)


def _control_has_user_value(widget: QWidget | None) -> bool:
    if isinstance(widget, QLineEdit):
        return bool(widget.text().strip())
    if isinstance(widget, QSpinBox):
        return widget.value() != widget.minimum()
    if isinstance(widget, QDoubleSpinBox):
        return abs(widget.value() - widget.minimum()) > 0.000001
    return True


def _set_control_text(widget: QWidget | None, text: str) -> None:
    if isinstance(widget, QLineEdit):
        widget.setText(text)
        return
    if isinstance(widget, QSpinBox):
        try:
            widget.setValue(int(float(text)))
        except ValueError:
            return
        return
    if isinstance(widget, QDoubleSpinBox):
        try:
            widget.setValue(float(text))
        except ValueError:
            return


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


def _option_text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _optional_float_text(text: str) -> float | None:
    text = text.strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _format_seconds(seconds: float) -> str:
    return f"{max(0.0, seconds):.3f}".rstrip("0").rstrip(".")


def _set_combo_value(combo: QComboBox, value: object) -> None:
    text = str(value)
    index = combo.findData(text)
    if index < 0:
        index = combo.findText(text)
    if index >= 0:
        combo.setCurrentIndex(index)


def _set_path_widget_text(widget: QWidget, text: str) -> None:
    if isinstance(widget, PathPicker):
        widget.set_text(text)
    elif isinstance(widget, QLineEdit):
        widget.setText(text)


def _parse_float_text(text: str, label: str) -> float:
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"{label}必须是数字") from exc
