from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

from desktop.app.core.paths import QSS_PATH
from desktop.app.ui.delegates import TextCellDelegate
from desktop.app.ui.panels.task_panel import _total_progress_summary
from desktop.app.ui.panels.task_panel import TaskPanel
from desktop.app.ui.widgets.task_table_model import TaskTableModel
from shared.contracts import Operation, TaskRecord, TaskStatus


def test_total_progress_summary_for_empty_queue() -> None:
    summary = _total_progress_summary([])

    assert summary.label == "无任务"
    assert summary.percent == 0
    assert not summary.indeterminate


def test_total_progress_summary_uses_queue_average() -> None:
    records = [
        TaskRecord(operation=Operation.convert, input_path=Path("done.mp4"), status=TaskStatus.succeeded, progress=1.0),
        TaskRecord(operation=Operation.convert, input_path=Path("running.mp4"), status=TaskStatus.running, progress=0.5),
        TaskRecord(operation=Operation.convert, input_path=Path("pending.mp4"), status=TaskStatus.pending, progress=0.0),
    ]

    summary = _total_progress_summary(records)

    assert summary.label == "总进度 1/3 · 50%"
    assert summary.percent == 50
    assert not summary.indeterminate


def test_total_progress_summary_handles_indeterminate_running_task() -> None:
    records = [
        TaskRecord(operation=Operation.convert, input_path=Path("done.mp4"), status=TaskStatus.succeeded, progress=1.0),
        TaskRecord(operation=Operation.convert, input_path=Path("running.mp4"), status=TaskStatus.running, progress=None),
    ]

    summary = _total_progress_summary(records)

    assert summary.label == "总进度 1/2 · 运行中"
    assert summary.indeterminate


def test_task_panel_processing_buttons_follow_task_state() -> None:
    _qt_app()
    panel = TaskPanel(TaskTableModel())

    assert not panel.start_button.isEnabled()
    assert not panel.cancel_button.isEnabled()
    assert not panel.cancel_queue_button.isEnabled()
    assert not panel.remove_pending_button.isEnabled()

    panel.set_start_enabled(True)
    assert panel.start_button.isEnabled()

    panel.set_busy(True)
    assert not panel.start_button.isEnabled()
    assert panel.cancel_button.isEnabled()

    panel.set_batch_buttons(pending_count=2, running=True)
    assert panel.cancel_queue_button.isEnabled()
    assert not panel.remove_pending_button.isEnabled()

    panel.set_busy(False)
    panel.set_batch_buttons(pending_count=2, running=False)
    assert panel.start_button.isEnabled()
    assert not panel.cancel_button.isEnabled()
    assert not panel.cancel_queue_button.isEnabled()
    assert panel.remove_pending_button.isEnabled()


def test_task_panel_uses_text_delegate_for_action_column() -> None:
    _qt_app()
    panel = TaskPanel(TaskTableModel())

    assert isinstance(panel.task_table.itemDelegateForColumn(2), TextCellDelegate)


def test_task_panel_places_total_progress_under_title() -> None:
    app = _qt_app()
    app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    panel = TaskPanel(TaskTableModel())
    panel.resize(1320, 360)
    panel.show()
    app.processEvents()

    progress_top = panel.total_progress_label.mapTo(panel, QPoint(0, 0)).y()
    title_top = panel.title_label.mapTo(panel, QPoint(0, 0)).y()
    title_right = panel.title_label.mapTo(panel, QPoint(panel.title_label.width(), 0)).x()
    start_left = panel.start_button.mapTo(panel, QPoint(0, 0)).x()
    start_top = panel.start_button.mapTo(panel, QPoint(0, 0)).y()

    assert progress_top > title_top
    assert panel.total_progress_bar.geometry().top() >= panel.total_progress_label.geometry().top() - 2
    assert start_left > title_right
    assert start_top <= title_top + panel.title_label.height() + 4

    panel.close()


def _qt_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        return QApplication(sys.argv)
    return app
