from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

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


def test_stack_panel_renders_steps_as_arrow_chain() -> None:
    app = _qt_app()
    app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    panel = StackPanel()
    emitted: list[int] = []
    selected: list[int] = []
    panel.move_down_requested.connect(emitted.append)
    panel.item_selected.connect(selected.append)
    panel.set_items(["基础 - 旋转/翻转", "基础 - 缩放+压缩 (outoverwrite)", "视频编辑 - 画面调整"])
    panel.resize(900, panel.maximumHeight())
    panel.show()
    app.processEvents()

    chips = panel.stack_chain.findChildren(QPushButton)
    arrows = panel.stack_chain.findChildren(QLabel, "stackArrow")

    assert len(chips) == 3
    assert len(arrows) == 2
    assert all(chip.property("role") == "stackChip" for chip in chips)
    assert min(chip.height() for chip in chips) >= 26
    assert panel.stack_chain.height() >= max(chip.height() for chip in chips) + 10
    assert panel.stack_chain.selected_index() == 2

    chips[1].click()
    assert selected == [1]
    assert panel.stack_chain.selected_index() == 1

    panel.stack_chain.select_index(0)
    panel.move_down_button.click()

    assert emitted == [0]
    assert panel.stack_chain.selected_index() == 1
    panel.close()


def _qt_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        return QApplication(sys.argv)
    return app
