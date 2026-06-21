from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPaintEvent, QPainter, QWheelEvent
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QListView,
    QPlainTextEdit,
    QSpinBox,
    QWidget,
)

from desktop.app.ui.widgets.operation_specs import RAW_PRESET_OPTIONS
from desktop.app.ui.widgets.path_picker import PathPicker


PARAMETER_FIELD_MAX_WIDTH = 560
SPINBOX_BUTTON_WIDTH = 28


class OperationFieldFactory:
    def __init__(
        self,
        *,
        file_browse_requested: Callable[[str, str], None],
        raw_preset_selected: Callable[[str], None],
    ) -> None:
        self._file_browse_requested = file_browse_requested
        self._raw_preset_selected = raw_preset_selected

    def create_widget(self, spec: dict[str, Any]) -> QWidget:
        kind = str(spec["kind"])
        if kind == "choice":
            combo = create_styled_combo_box()
            for value in spec["choices"]:
                combo.addItem(str(value), str(value))
            default = str(spec.get("default", ""))
            index = combo.findData(default)
            if index >= 0:
                combo.setCurrentIndex(index)
            return combo
        if kind == "int":
            spin = NoWheelSpinBox()
            spin.setRange(int(spec["min"]), int(spec["max"]))
            spin.setValue(int(spec["default"]))
            return spin
        if kind == "float":
            spin = NoWheelDoubleSpinBox()
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
            combo = create_styled_combo_box()
            combo.addItem("不使用示例命令", "")
            for label, args in RAW_PRESET_OPTIONS:
                combo.addItem(label, args)
            combo.currentTextChanged.connect(lambda _text: self._raw_preset_selected(str(combo.currentData())))
            return combo
        return QLabel(f"Unsupported field: {kind}")

    def _create_file_widget(self, spec: dict[str, Any]) -> PathPicker:
        filter_text = str(spec.get("filter", "所有文件 (*.*)"))
        field_name = str(spec["name"])
        picker = PathPicker(placeholder=str(spec.get("placeholder", "")), button_text="选择")
        picker.browse_requested.connect(lambda: self._file_browse_requested(field_name, filter_text))
        return picker


def configure_parameter_field(widget: QWidget) -> None:
    if isinstance(widget, (QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit, PathPicker)):
        widget.setMaximumWidth(PARAMETER_FIELD_MAX_WIDTH)


def create_styled_combo_box() -> QComboBox:
    combo = QComboBox()
    popup_view = QListView()
    popup_view.setObjectName("comboPopupView")
    popup_view.setUniformItemSizes(True)
    popup_view.setMouseTracking(True)
    combo.setView(popup_view)
    return combo


class NoWheelSpinBox(QSpinBox):
    def __init__(self) -> None:
        super().__init__()
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.PlusMinus)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802 - Qt override name
        event.ignore()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 - Qt override name
        super().paintEvent(event)
        _draw_spinbox_symbols(self)


class NoWheelDoubleSpinBox(QDoubleSpinBox):
    def __init__(self) -> None:
        super().__init__()
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.PlusMinus)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802 - Qt override name
        event.ignore()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 - Qt override name
        super().paintEvent(event)
        _draw_spinbox_symbols(self)


def _draw_spinbox_symbols(widget: QSpinBox | QDoubleSpinBox) -> None:
    button_rect = QRect(widget.width() - SPINBOX_BUTTON_WIDTH, 0, SPINBOX_BUTTON_WIDTH, widget.height())
    top_rect = QRect(button_rect.left(), button_rect.top(), button_rect.width(), button_rect.height() // 2)
    bottom_rect = QRect(
        button_rect.left(),
        top_rect.bottom() + 1,
        button_rect.width(),
        button_rect.height() - top_rect.height(),
    )
    painter = QPainter(widget)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    font = painter.font()
    font.setBold(True)
    font.setPointSize(max(font.pointSize(), 10))
    painter.setFont(font)
    painter.setPen(QColor("#d8e0ef" if widget.isEnabled() else "#687386"))
    painter.drawText(top_rect, Qt.AlignmentFlag.AlignCenter, "+")
    painter.drawText(bottom_rect, Qt.AlignmentFlag.AlignCenter, "-")
    painter.end()
