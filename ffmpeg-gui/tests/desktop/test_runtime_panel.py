from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

from desktop.app.core.paths import QSS_PATH
from desktop.app.ui.components import PanelFrame
from desktop.app.ui.panels.command_preview_panel import CommandPreviewPanel
from desktop.app.ui.panels.runtime_panel import RuntimePanel
from desktop.app.ui.panels.stack_panel import StackPanel
from desktop.app.ui.panels.task_panel import TaskPanel
from desktop.app.ui.widgets.task_table_model import TaskTableModel


def test_runtime_panel_uses_panel_frame_and_keeps_output_action() -> None:
    _qt_app()
    panel = RuntimePanel()
    emitted: list[bool] = []
    panel.output_dir_requested.connect(lambda: emitted.append(True))

    panel.output_dir_button.click()

    assert isinstance(panel, PanelFrame)
    assert panel.title_label.text() == "内容选择"
    assert panel.body_layout().count() >= 2
    assert emitted == [True]


def test_secondary_panels_use_panel_frame_shells() -> None:
    _qt_app()
    command_panel = CommandPreviewPanel()
    stack_panel = StackPanel()
    task_panel = TaskPanel(TaskTableModel())

    assert isinstance(command_panel, PanelFrame)
    assert isinstance(stack_panel, PanelFrame)
    assert isinstance(task_panel, PanelFrame)
    assert command_panel.title_label.text() == "命令预览"
    assert stack_panel.title_label.text() == "Stack 队列"
    assert task_panel.title_label.text() == "任务队列"


def test_command_preview_keeps_input_bottom_border_visible() -> None:
    app = _qt_app()
    app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    panel = CommandPreviewPanel()
    panel.resize(1400, panel.minimumHeight())
    panel.show()
    app.processEvents()

    edit_bottom = panel.preview_edit.mapTo(panel, QPoint(0, panel.preview_edit.height())).y()

    assert panel.height() >= 96
    assert panel.height() - edit_bottom >= 8
    panel.close()


def _qt_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        return QApplication(sys.argv)
    return app
