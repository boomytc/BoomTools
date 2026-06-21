from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QFrame, QWidget

from desktop.app.core.paths import QSS_PATH
from desktop.app.ui.main_window import MainWindow
from desktop.app.ui.widgets.task_table_model import TaskTableModel


def test_main_window_builds_dashboard_layout_host() -> None:
    app = _qt_app()
    app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    window = MainWindow(TaskTableModel())
    window.show()
    app.processEvents()

    dashboard = window.findChild(QWidget, "dashboardLayoutHost")

    assert dashboard is window.dashboard_layout
    assert window.runtime_panel.property("panel_id") == "content"
    assert window.operation_panel.operation_form.operation_selector.property("panel_id") == "operation"
    assert window.operation_panel.operation_form.parameter_form.property("panel_id") == "parameters"
    assert window.operation_panel.stack_panel.property("panel_id") == "stack"
    assert window.command_preview_panel.property("panel_id") == "command_preview"
    assert window.task_panel.property("panel_id") == "tasks"

    window.close()


def test_main_window_default_panel_order_and_resize_bounds() -> None:
    app = _qt_app()
    app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    window = MainWindow(TaskTableModel())
    window.resize(1320, 1000)
    window.show()
    app.processEvents()

    masthead = window.findChild(QFrame, "masthead")
    assert masthead is not None
    runtime_top = _top_in_window(window.runtime_panel, window)
    operation_top = _top_in_window(window.operation_panel, window)
    command_top = _top_in_window(window.command_preview_panel, window)
    task_top = _top_in_window(window.task_panel, window)
    operation_selector = window.operation_panel.operation_form.operation_selector
    parameter_form = window.operation_panel.operation_form.parameter_form
    operation_selector_top = _top_in_window(operation_selector, window)
    parameter_form_top = _top_in_window(parameter_form, window)
    command_bottom = _bottom_in_window(window.command_preview_panel, window)
    parameter_bottom = _bottom_in_window(parameter_form, window)

    assert runtime_top > _top_in_window(masthead, window)
    assert runtime_top < operation_top < command_top < task_top
    assert command_top < _bottom_in_window(window.operation_panel, window)
    assert abs(operation_selector_top - parameter_form_top) <= 2
    assert abs(parameter_bottom - command_bottom) <= 2
    assert abs(window.command_preview_panel.width() - operation_selector.width()) <= 2
    assert window.task_panel.height() > window.task_panel.minimumHeight()
    assert window.operation_panel.height() <= window.operation_panel.sizeHint().height() + 2

    window.resize(1320, 760)
    app.processEvents()

    assert window.runtime_panel.height() <= window.runtime_panel.maximumHeight()
    assert window.operation_panel.height() <= window.operation_panel.sizeHint().height() + 2
    assert window.task_panel.height() >= window.task_panel.minimumHeight()
    window.close()


def _top_in_window(widget: QWidget, window: MainWindow) -> int:
    return widget.mapTo(window, QPoint(0, 0)).y()


def _bottom_in_window(widget: QWidget, window: MainWindow) -> int:
    return widget.mapTo(window, QPoint(0, widget.height())).y()


def _qt_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        return QApplication(sys.argv)
    return app
