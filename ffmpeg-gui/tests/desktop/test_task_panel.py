from __future__ import annotations

from pathlib import Path

from desktop.app.ui.panels.task_panel import _total_progress_summary
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
