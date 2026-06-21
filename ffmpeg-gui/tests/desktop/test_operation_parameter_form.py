from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QComboBox, QListView

from desktop.app.ui.widgets.operation_parameter_form import OperationParameterForm
from shared.contracts import Operation


def test_parameter_form_keeps_height_across_raw_and_empty_operations() -> None:
    app = _qt_app()
    form = OperationParameterForm()
    form.resize(520, 360)
    form.show()
    app.processEvents()
    initial_height = form.height()

    form.set_operation(Operation.raw)
    app.processEvents()

    assert form.height() == initial_height
    assert form.parameter_scroll_area.verticalScrollBar().maximum() > 0

    form.set_operation(Operation.media_info)
    app.processEvents()

    assert form.height() == initial_height
    assert not form.fields_section.title_label.isVisible()
    assert form.fields_section.empty_label.isVisible()
    form.close()


def test_parameter_form_collects_options_and_extra_inputs(tmp_path: Path) -> None:
    form = OperationParameterForm()
    subtitle_path = tmp_path / "字幕 文件.srt"
    subtitle_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi", encoding="utf-8")

    form.set_operation(Operation.subtitles)
    form.start_seconds_edit.setText("1.5")
    form.set_subtitle_path(str(subtitle_path))

    operation, options, extra_inputs = form.collect()

    assert operation is Operation.subtitles
    assert options["start_seconds"] == 1.5
    assert options["mode"] == "soft"
    assert extra_inputs["subtitle"] == subtitle_path


def test_parameter_form_spinboxes_ignore_wheel_events() -> None:
    app = _qt_app()
    form = OperationParameterForm()
    form.set_operation(Operation.gif)
    fps_spin = form.controls()["fps"]
    fps_value = fps_spin.value()  # type: ignore[attr-defined]

    QApplication.sendEvent(fps_spin, _wheel_up_event())  # type: ignore[arg-type]

    assert fps_spin.value() == fps_value  # type: ignore[attr-defined]
    app.processEvents()


def test_parameter_form_comboboxes_use_styled_popup_views() -> None:
    _qt_app()
    form = OperationParameterForm()
    form.set_operation(Operation.raw)
    raw_preset_combo = form.controls()["raw_preset"]

    assert isinstance(raw_preset_combo, QComboBox)
    assert isinstance(raw_preset_combo.view(), QListView)
    assert raw_preset_combo.view().objectName() == "comboPopupView"
    assert raw_preset_combo.view().uniformItemSizes()


def _qt_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        return QApplication(sys.argv)
    return app


def _wheel_up_event() -> QWheelEvent:
    return QWheelEvent(
        QPointF(4, 4),
        QPointF(4, 4),
        QPoint(0, 0),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.ScrollUpdate,
        False,
    )
