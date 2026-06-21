from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QComboBox, QFrame, QListView

from desktop.app.core.paths import QSS_PATH
from desktop.app.ui.components import PanelFrame
from desktop.app.ui.main_window import MainWindow
from desktop.app.ui.panels.operation_panel import OperationPanel
from desktop.app.ui.widgets.task_table_model import TaskTableModel
from shared.contracts import Operation


def test_stack_mode_keeps_operation_form_readable() -> None:
    app = _qt_app()
    app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    panel = OperationPanel()
    panel.resize(1320, 500)

    panel.set_stack_mode(True)
    panel.show()
    app.processEvents()

    assert panel.stack_panel.isVisible()
    assert panel.stack_panel.height() <= panel.stack_panel.maximumHeight()
    assert panel.operation_form.height() >= panel.operation_form.minimumHeight()
    selector = panel.operation_form.operation_selector
    assert min(button.height() for button in selector.operation_buttons().values()) >= 28
    assert selector.operation_scroll_area.verticalScrollBar().maximum() > 0
    assert selector.operation_scroll_area.horizontalScrollBar().maximum() == 0

    panel.close()


def test_parameter_area_scrolls_without_resizing_panel() -> None:
    app = _qt_app()
    app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    panel = OperationPanel()
    panel.resize(1320, 640)
    panel.show()
    app.processEvents()

    parameter_form = panel.operation_form.parameter_form
    initial_height = parameter_form.height()
    form_height = panel.operation_form.height()
    label = parameter_form.selected_operation_label

    panel.operation_form.select_operation(Operation.raw)
    app.processEvents()

    assert parameter_form.height() == initial_height
    assert panel.operation_form.height() == form_height
    assert label.height() <= label.sizeHint().height() + 4
    assert parameter_form.parameter_scroll_area.verticalScrollBar().maximum() > 0
    assert parameter_form.parameter_scroll_area.horizontalScrollBar().maximum() == 0

    panel.operation_form.select_operation(Operation.media_info)
    app.processEvents()

    assert parameter_form.height() == initial_height
    assert panel.operation_form.height() == form_height

    panel.close()


def test_parameter_fields_keep_gutter_from_scrollbar() -> None:
    app = _qt_app()
    app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    panel = OperationPanel()
    panel.resize(1320, 640)
    panel.show()
    app.processEvents()

    panel.operation_form.select_operation(Operation.resize_compress)
    app.processEvents()

    form = panel.operation_form.parameter_form
    width_field = form.controls()["width"]
    content_margins = form.parameter_content_widget.layout().contentsMargins()

    assert form.parameter_scroll_area.viewportMargins().right() >= 8
    assert content_margins.right() >= 12
    assert form.parameter_content_widget.width() <= 680
    assert width_field.maximumWidth() <= 560
    assert width_field.width() <= 560

    panel.close()


def test_parameter_spinboxes_ignore_wheel_events() -> None:
    app = _qt_app()
    app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    panel = OperationPanel()
    panel.show()
    app.processEvents()

    panel.operation_form.select_operation(Operation.gif)
    app.processEvents()
    fps_spin = panel.operation_form.parameter_form.controls()["fps"]
    fps_value = fps_spin.value()  # type: ignore[attr-defined]
    QApplication.sendEvent(fps_spin, _wheel_up_event())  # type: ignore[arg-type]

    panel.operation_form.select_operation(Operation.fade)
    app.processEvents()
    fade_spin = panel.operation_form.parameter_form.controls()["fade_in_seconds"]
    fade_value = fade_spin.value()  # type: ignore[attr-defined]
    QApplication.sendEvent(fade_spin, _wheel_up_event())  # type: ignore[arg-type]

    assert fps_spin.value() == fps_value  # type: ignore[attr-defined]
    assert fade_spin.value() == fade_value  # type: ignore[attr-defined]

    panel.close()


def test_parameter_comboboxes_use_styled_popup_views() -> None:
    app = _qt_app()
    app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    panel = OperationPanel()
    panel.show()
    app.processEvents()

    panel.operation_form.select_operation(Operation.resize_compress)
    app.processEvents()
    preset_combo = panel.operation_form.parameter_form.controls()["preset"]

    panel.operation_form.select_operation(Operation.raw)
    app.processEvents()
    raw_preset_combo = panel.operation_form.parameter_form.controls()["raw_preset"]

    for combo in (preset_combo, raw_preset_combo):
        assert isinstance(combo, QComboBox)
        assert isinstance(combo.view(), QListView)
        assert combo.view().objectName() == "comboPopupView"
        assert combo.view().uniformItemSizes()

    panel.close()


def test_operation_and_parameter_panels_use_compact_internal_titles() -> None:
    app = _qt_app()
    app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    panel = OperationPanel()
    panel.resize(1320, 500)
    panel.show()
    app.processEvents()

    form = panel.operation_form
    operation_margins = form.operation_selector.layout().contentsMargins()
    parameter_margins = form.parameter_form.layout().contentsMargins()

    assert isinstance(form.operation_selector, PanelFrame)
    assert isinstance(form.parameter_form, PanelFrame)
    assert form.operation_selector.objectName() == "operationFrame"
    assert form.parameter_form.objectName() == "parameterFrame"
    assert form.operation_selector.title_label.text() == "处理动作"
    assert form.parameter_form.title_label.text() == "参数"
    assert operation_margins.top() <= 10
    assert parameter_margins.top() <= 10
    assert operation_margins.left() == parameter_margins.left()
    assert operation_margins.right() == parameter_margins.right()

    panel.close()


def test_operation_form_uses_panel_frame_selectors() -> None:
    _qt_app()
    panel = OperationPanel()
    form = panel.operation_form

    assert form.operation_selector.objectName() == "operationFrame"
    assert form.parameter_form.objectName() == "parameterFrame"
    panel.close()


def test_operation_form_places_command_preview_under_selector() -> None:
    app = _qt_app()
    app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    panel = OperationPanel()
    panel.resize(1320, 760)
    panel.show()
    app.processEvents()

    selector = panel.operation_form.operation_selector
    command_preview = panel.command_preview_panel
    parameter_form = panel.operation_form.parameter_form

    assert panel.operation_form.geometry().top() == 0
    assert panel.operation_form.height() == panel.operation_form.sizeHint().height()
    assert command_preview.geometry().left() == selector.geometry().left()
    assert command_preview.geometry().top() > selector.geometry().bottom()
    assert abs(command_preview.width() - selector.width()) <= 2
    assert parameter_form.geometry().top() == selector.geometry().top()
    assert abs(parameter_form.geometry().bottom() - command_preview.geometry().bottom()) <= 2
    assert parameter_form.height() > parameter_form.sizeHint().height()
    assert parameter_form.parameter_scroll_area.height() > 164

    panel.close()


def test_main_window_does_not_assign_extra_height_to_operation_panel() -> None:
    app = _qt_app()
    app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    window = MainWindow(TaskTableModel())
    window.resize(1320, 1000)
    window.show()
    app.processEvents()

    masthead = window.findChild(QFrame, "masthead")
    assert masthead is not None
    assert masthead.height() <= masthead.sizeHint().height() + 2
    runtime_bottom = window.runtime_panel.geometry().bottom()
    operation_top = window.operation_panel.geometry().top()
    assert operation_top - runtime_bottom <= 12
    assert window.operation_panel.height() <= window.operation_panel.sizeHint().height() + 2
    assert window.operation_panel.operation_form.geometry().top() == 0
    assert window.task_panel.height() > window.task_panel.minimumHeight()

    window.close()


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
