from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication

from desktop.app.ui.widgets.progress import ProgressSummaryWidget, progress_bar_rect, status_progress_visual
from shared.contracts import TaskStatus


def test_progress_summary_widget_applies_indeterminate_state() -> None:
    _qt_app()
    widget = ProgressSummaryWidget()

    widget.set_summary(
        label="总进度 1/2 · 运行中",
        tooltip="当前任务无法估算精确百分比",
        percent=0,
        indeterminate=True,
        state="running",
    )

    assert widget.label.text() == "总进度 1/2 · 运行中"
    assert widget.label.toolTip() == "当前任务无法估算精确百分比"
    assert widget.progress_bar.toolTip() == "当前任务无法估算精确百分比"
    assert widget.progress_bar.minimum() == 0
    assert widget.progress_bar.maximum() == 0
    assert widget.property("state") == "running"
    assert widget.label.property("state") == "running"
    assert widget.progress_bar.property("state") == "running"


def test_progress_summary_widget_clamps_determinate_percent() -> None:
    _qt_app()
    widget = ProgressSummaryWidget()

    widget.set_summary(label="总进度 2/2 · 100%", tooltip="完成", percent=150, state="success")

    assert widget.progress_bar.minimum() == 0
    assert widget.progress_bar.maximum() == 100
    assert widget.progress_bar.value() == 100
    assert widget.progress_bar.property("state") == "success"


def test_status_progress_visual_maps_terminal_statuses() -> None:
    failed_visual = status_progress_visual(TaskStatus.failed)

    assert failed_visual is not None
    assert failed_visual.label == "失败"
    assert status_progress_visual(TaskStatus.running) is None


def test_progress_bar_rect_uses_stable_cell_margins() -> None:
    rect = progress_bar_rect(QRect(0, 0, 120, 54))

    assert rect.x() == 10
    assert rect.width() == 100
    assert 16 <= rect.height() <= 22


def _qt_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        return QApplication(sys.argv)
    return app
