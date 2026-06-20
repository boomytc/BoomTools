from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QTableView, QVBoxLayout

from desktop.app.ui.delegates import MediaSummaryDelegate, ProgressBarDelegate, StatusBadgeDelegate
from desktop.app.ui.widgets.task_table_model import TaskTableModel
from shared.contracts import TERMINAL_STATUSES, TaskRecord, TaskStatus


class TaskPanel(QFrame):
    def __init__(self, task_model: TaskTableModel) -> None:
        super().__init__()
        self._task_model = task_model
        self.setObjectName("taskPanel")
        self.setMinimumHeight(184)
        self.setMaximumHeight(222)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        title_label = QLabel("任务队列")
        title_label.setObjectName("sectionTitle")
        self.total_progress_label = QLabel("无任务")
        self.total_progress_label.setObjectName("totalProgressLabel")
        self.total_progress_bar = QProgressBar()
        self.total_progress_bar.setObjectName("totalProgressBar")
        self.total_progress_bar.setRange(0, 100)
        self.total_progress_bar.setValue(0)
        self.total_progress_bar.setTextVisible(False)
        self.total_progress_bar.setFixedWidth(132)
        header_row.addWidget(title_label)
        header_row.addStretch(1)
        header_row.addWidget(self.total_progress_label)
        header_row.addWidget(self.total_progress_bar)
        layout.addLayout(header_row)

        self.task_table = QTableView()
        self.task_table.setObjectName("taskTable")
        self.task_table.setModel(task_model)
        self.task_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.horizontalHeader().setStretchLastSection(True)
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.verticalHeader().setDefaultSectionSize(38)
        self.task_table.setShowGrid(False)
        self.task_table.setSortingEnabled(False)
        self.task_table.setItemDelegateForColumn(0, StatusBadgeDelegate(self.task_table))
        self.task_table.setItemDelegateForColumn(2, MediaSummaryDelegate(self.task_table))
        self.task_table.setItemDelegateForColumn(5, ProgressBarDelegate(self.task_table))
        self.task_table.resizeColumnsToContents()
        self.task_table.setColumnWidth(0, 86)
        self.task_table.setColumnWidth(1, 170)
        self.task_table.setColumnWidth(2, 280)
        self.task_table.setColumnWidth(3, 130)
        self.task_table.setColumnWidth(4, 130)
        self.task_table.setColumnWidth(5, 120)
        self.task_table.setMinimumHeight(112)
        layout.addWidget(self.task_table)

        task_model.modelReset.connect(self.refresh_total_progress)
        task_model.rowsInserted.connect(lambda *_args: self.refresh_total_progress())
        task_model.rowsRemoved.connect(lambda *_args: self.refresh_total_progress())
        task_model.dataChanged.connect(lambda *_args: self.refresh_total_progress())
        self.refresh_total_progress()

    def refresh_total_progress(self) -> None:
        summary = _total_progress_summary(self._task_model.records())
        if summary.indeterminate:
            self.total_progress_bar.setRange(0, 0)
        else:
            self.total_progress_bar.setRange(0, 100)
            self.total_progress_bar.setValue(summary.percent)
        self.total_progress_label.setText(summary.label)
        self.total_progress_label.setToolTip(summary.tooltip)
        self.total_progress_bar.setToolTip(summary.tooltip)


class _TotalProgressSummary:
    def __init__(self, *, label: str, tooltip: str, percent: int, indeterminate: bool = False) -> None:
        self.label = label
        self.tooltip = tooltip
        self.percent = percent
        self.indeterminate = indeterminate


def _total_progress_summary(records: list[TaskRecord]) -> _TotalProgressSummary:
    total = len(records)
    if total == 0:
        return _TotalProgressSummary(label="无任务", tooltip="当前没有任务", percent=0)

    done = sum(1 for record in records if record.status in TERMINAL_STATUSES)
    if any(record.status is TaskStatus.running and record.progress is None for record in records):
        return _TotalProgressSummary(
            label=f"总进度 {done}/{total} · 运行中",
            tooltip=f"总进度：{done}/{total}，当前任务无法估算精确百分比",
            percent=0,
            indeterminate=True,
        )

    progress_total = sum(_record_progress_value(record) for record in records)
    percent = max(0, min(100, int(round(progress_total / total * 100))))
    label = f"总进度 {done}/{total} · {percent}%"
    tooltip = f"总进度：{done}/{total}，{percent}%"
    return _TotalProgressSummary(label=label, tooltip=tooltip, percent=percent)


def _record_progress_value(record: TaskRecord) -> float:
    if record.status in TERMINAL_STATUSES:
        return 1.0
    if isinstance(record.progress, (int, float)):
        return max(0.0, min(float(record.progress), 1.0))
    return 0.0
