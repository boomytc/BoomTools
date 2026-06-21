from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QFrame

from desktop.app.core.paths import QSS_PATH
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
    assert min(button.height() for button in panel.operation_form._operation_buttons.values()) >= 28
    assert panel.operation_form.operation_scroll_area.verticalScrollBar().maximum() > 0
    assert panel.operation_form.operation_scroll_area.horizontalScrollBar().maximum() == 0

    panel.close()


def test_parameter_area_scrolls_without_resizing_panel() -> None:
    app = _qt_app()
    app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    panel = OperationPanel()
    panel.resize(1320, 640)
    panel.show()
    app.processEvents()

    initial_height = panel.operation_form.parameters_group.height()
    form_height = panel.operation_form.height()
    label = panel.operation_form.selected_operation_label

    panel.operation_form._select_operation(Operation.raw)
    app.processEvents()

    assert panel.operation_form.parameters_group.height() == initial_height
    assert panel.operation_form.height() == form_height
    assert label.height() <= label.sizeHint().height() + 4
    assert panel.operation_form.parameter_scroll_area.verticalScrollBar().maximum() > 0
    assert panel.operation_form.parameter_scroll_area.horizontalScrollBar().maximum() == 0

    panel.operation_form._select_operation(Operation.media_info)
    app.processEvents()

    assert panel.operation_form.parameters_group.height() == initial_height
    assert panel.operation_form.height() == form_height

    panel.close()


def test_operation_form_does_not_expand_into_extra_window_height() -> None:
    app = _qt_app()
    app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    panel = OperationPanel()
    panel.resize(1320, 760)
    panel.show()
    app.processEvents()

    assert panel.operation_form.geometry().top() == 0
    assert panel.operation_form.height() == panel.operation_form.sizeHint().height()
    assert panel.operation_form.parameters_group.height() == panel.operation_form.parameters_group.sizeHint().height()

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
