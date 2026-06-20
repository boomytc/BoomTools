from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QModelIndex, QPoint, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMenu, QProgressBar, QTableView, QVBoxLayout

from desktop.app.ui.delegates import MediaSummaryDelegate, ProgressBarDelegate, StatusBadgeDelegate
from desktop.app.ui.widgets.task_table_model import TaskTableModel
from shared.contracts import TERMINAL_STATUSES, TaskRecord, TaskStatus


class TaskPanel(QFrame):
    open_output_requested = Signal()
    open_output_dir_requested = Signal()
    copy_output_path_requested = Signal()

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
        file_delegate = MediaSummaryDelegate(self.task_table)
        self.task_table.setItemDelegateForColumn(1, file_delegate)
        self.task_table.setItemDelegateForColumn(3, file_delegate)
        self.task_table.setItemDelegateForColumn(4, ProgressBarDelegate(self.task_table))
        self.task_table.resizeColumnsToContents()
        self.task_table.setColumnWidth(0, 86)
        self.task_table.setColumnWidth(1, 300)
        self.task_table.setColumnWidth(2, 150)
        self.task_table.setColumnWidth(3, 240)
        self.task_table.setColumnWidth(4, 120)
        self.task_table.verticalHeader().setDefaultSectionSize(54)
        self.task_table.setMinimumHeight(126)
        self.task_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        layout.addWidget(self.task_table)
        self.task_table.doubleClicked.connect(self._handle_table_double_clicked)
        self.task_table.customContextMenuRequested.connect(self._open_context_menu)

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

    def selected_output_path(self) -> Path | None:
        selection_model = self.task_table.selectionModel()
        if selection_model is None:
            return None
        selected_rows = selection_model.selectedRows()
        if not selected_rows:
            return None
        row = selected_rows[0].row()
        records = self._task_model.records()
        if row < 0 or row >= len(records):
            return None
        return records[row].output_path

    def output_path_exists(self) -> bool:
        output_path = self.selected_output_path()
        return bool(output_path and output_path.exists())

    def _handle_table_double_clicked(self, index: QModelIndex) -> None:
        if index.column() == 3 and self.output_path_exists():
            self.open_output_requested.emit()

    def _open_context_menu(self, position: QPoint) -> None:
        index = self.task_table.indexAt(position)
        if index.isValid():
            self.task_table.selectRow(index.row())

        has_output = self.output_path_exists()
        menu = QMenu(self.task_table)
        open_file_action = menu.addAction("打开输出文件")
        open_dir_action = menu.addAction("打开输出目录")
        copy_path_action = menu.addAction("复制输出路径")
        open_file_action.setEnabled(has_output)
        open_dir_action.setEnabled(has_output)
        copy_path_action.setEnabled(has_output)
        open_file_action.triggered.connect(self.open_output_requested.emit)
        open_dir_action.triggered.connect(self.open_output_dir_requested.emit)
        copy_path_action.triggered.connect(self.copy_output_path_requested.emit)
        menu.exec(self.task_table.viewport().mapToGlobal(position))


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
