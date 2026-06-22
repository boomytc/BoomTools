from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QHeaderView

from desktop.app.core.paths import QSS_PATH
from desktop.app.ui.delegates import MediaSummaryDelegate, ProgressBarDelegate, RemoveActionDelegate, TextCellDelegate
from desktop.app.ui.panels.task_panel import _total_progress_summary
from desktop.app.ui.panels.task_panel import TaskPanel
from desktop.app.ui.widgets.progress import ProgressSummaryWidget
from desktop.app.ui.widgets.task_table_model import TaskTableModel
from shared.contracts import Operation, TaskRecord, TaskStatus


def test_total_progress_summary_for_empty_queue() -> None:
    summary = _total_progress_summary([])

    assert summary.label == "无任务"
    assert summary.percent == 0
    assert not summary.indeterminate
    assert summary.state == "empty"


def test_total_progress_summary_uses_queue_average() -> None:
    records = [
        TaskRecord(
            operation=Operation.convert,
            input_path=Path("done.mp4"),
            status=TaskStatus.succeeded,
            progress=1.0,
        ),
        TaskRecord(
            operation=Operation.convert,
            input_path=Path("running.mp4"),
            status=TaskStatus.running,
            progress=0.5,
        ),
        TaskRecord(
            operation=Operation.convert,
            input_path=Path("pending.mp4"),
            status=TaskStatus.pending,
            progress=0.0,
        ),
    ]

    summary = _total_progress_summary(records)

    assert summary.label == "总进度 1/3 · 50%"
    assert summary.percent == 50
    assert not summary.indeterminate
    assert summary.state == "running"


def test_total_progress_summary_handles_indeterminate_running_task() -> None:
    records = [
        TaskRecord(
            operation=Operation.convert,
            input_path=Path("done.mp4"),
            status=TaskStatus.succeeded,
            progress=1.0,
        ),
        TaskRecord(
            operation=Operation.convert,
            input_path=Path("running.mp4"),
            status=TaskStatus.running,
            progress=None,
        ),
    ]

    summary = _total_progress_summary(records)

    assert summary.label == "总进度 1/2 · 运行中"
    assert summary.indeterminate
    assert summary.state == "running"


def test_total_progress_summary_exposes_failure_state() -> None:
    records = [
        TaskRecord(operation=Operation.convert, input_path=Path("failed.mp4"), status=TaskStatus.failed, progress=0.0),
    ]

    summary = _total_progress_summary(records)

    assert summary.label == "总进度 1/1 · 100%"
    assert summary.percent == 100
    assert summary.state == "failure"


def test_task_panel_processing_buttons_follow_task_state() -> None:
    _qt_app()
    panel = TaskPanel(TaskTableModel())

    assert not panel.start_button.isEnabled()
    assert not panel.cancel_button.isEnabled()
    assert not panel.cancel_queue_button.isEnabled()
    assert not panel.remove_pending_button.isEnabled()
    assert not panel.zip_results_button.isEnabled()
    assert panel.result_action_bar.isHidden()

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

    panel.set_zip_results_enabled(True)
    assert not panel.zip_results_button.isEnabled()
    assert panel.zip_results_button.text() == "无批次可打包"

    panel.set_zip_results_enabled(False, running=True)
    assert not panel.zip_results_button.isEnabled()
    assert panel.zip_results_button.text() == "正在打包..."

    panel.set_recent_batch_results(
        "最近批次：成功 1 · 失败 0 · 取消 0 · 已打包 0",
        tooltip="最近批次总数：1",
        has_batch=True,
        has_successful_outputs=True,
    )
    panel.set_zip_results_enabled(True)
    assert not panel.result_action_bar.isHidden()
    assert panel.zip_results_button.text() == "打包成功结果"
    assert panel.copy_batch_paths_button.isEnabled()
    assert panel.open_batch_dir_button.isEnabled()
    assert panel.locate_batch_button.isEnabled()

    panel.set_recent_batch_results(
        "最近批次：成功 0 · 失败 1 · 取消 0 · 已打包 0",
        tooltip="最近批次总数：1",
        has_batch=True,
        has_successful_outputs=False,
    )
    panel.set_zip_results_enabled(False)
    assert panel.zip_results_button.text() == "无成功结果"
    assert not panel.copy_batch_paths_button.isEnabled()

    panel.set_dense_mode(True)
    assert panel.result_action_bar.isHidden()


def test_task_panel_uses_text_delegate_for_action_column() -> None:
    _qt_app()
    panel = TaskPanel(TaskTableModel())

    assert isinstance(panel.task_table.itemDelegateForColumn(2), TextCellDelegate)


def test_task_panel_configures_queue_columns_and_delegates() -> None:
    _qt_app()
    panel = TaskPanel(TaskTableModel())
    header = panel.task_table.horizontalHeader()

    assert header.sectionResizeMode(0) == QHeaderView.ResizeMode.Stretch
    assert header.sectionResizeMode(1) == QHeaderView.ResizeMode.Stretch
    assert header.sectionResizeMode(2) == QHeaderView.ResizeMode.Fixed
    assert header.sectionResizeMode(3) == QHeaderView.ResizeMode.Fixed
    assert header.sectionResizeMode(4) == QHeaderView.ResizeMode.Fixed
    assert isinstance(panel.task_table.itemDelegateForColumn(0), MediaSummaryDelegate)
    assert isinstance(panel.task_table.itemDelegateForColumn(1), MediaSummaryDelegate)
    assert isinstance(panel.task_table.itemDelegateForColumn(2), TextCellDelegate)
    assert isinstance(panel.task_table.itemDelegateForColumn(3), ProgressBarDelegate)
    assert isinstance(panel.task_table.itemDelegateForColumn(4), RemoveActionDelegate)


def test_task_panel_uses_progress_summary_widget() -> None:
    _qt_app()
    panel = TaskPanel(TaskTableModel())

    assert isinstance(panel.total_progress, ProgressSummaryWidget)
    assert panel.total_progress_label is panel.total_progress.label
    assert panel.total_progress_bar is panel.total_progress.progress_bar


def test_task_panel_remove_column_emits_task_id_only_for_removable_rows() -> None:
    _qt_app()
    model = TaskTableModel()
    ready_record = TaskRecord(operation=Operation.convert, input_path=Path("ready.mp4"), status=TaskStatus.ready)
    running_record = TaskRecord(operation=Operation.convert, input_path=Path("running.mp4"), status=TaskStatus.running)
    model.append_record(ready_record)
    model.append_record(running_record)
    panel = TaskPanel(model)
    emitted: list[str] = []
    panel.remove_task_requested.connect(emitted.append)

    panel._handle_table_clicked(model.index(0, 4))
    panel._handle_table_clicked(model.index(1, 4))

    assert emitted == [ready_record.task_id]


def test_task_panel_selects_rows_by_task_ids() -> None:
    _qt_app()
    model = TaskTableModel()
    first = TaskRecord(operation=Operation.convert, input_path=Path("first.mp4"), status=TaskStatus.succeeded)
    second = TaskRecord(operation=Operation.convert, input_path=Path("second.mp4"), status=TaskStatus.failed)
    third = TaskRecord(operation=Operation.convert, input_path=Path("third.mp4"), status=TaskStatus.succeeded)
    for record in (first, second, third):
        model.append_record(record)
    panel = TaskPanel(model)

    selected_count = panel.select_task_ids({first.task_id, third.task_id})

    assert selected_count == 2
    assert [index.row() for index in panel.task_table.selectionModel().selectedRows()] == [0, 2]


def test_task_panel_emits_selected_task_id_when_current_row_changes() -> None:
    _qt_app()
    model = TaskTableModel()
    first = TaskRecord(operation=Operation.convert, input_path=Path("first.mp4"), status=TaskStatus.ready)
    second = TaskRecord(operation=Operation.convert, input_path=Path("second.mp4"), status=TaskStatus.ready)
    model.append_record(first)
    model.append_record(second)
    panel = TaskPanel(model)
    emitted: list[str] = []
    panel.task_selection_changed.connect(emitted.append)

    panel.task_table.selectRow(1)

    assert emitted[-1] == second.task_id


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
