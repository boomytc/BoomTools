from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QItemSelection, QItemSelectionModel, QModelIndex, QPoint, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QTableView,
    QWidget,
)

from desktop.app.ui.components import PanelActionBar, PanelFrame
from desktop.app.ui.delegates import MediaSummaryDelegate, ProgressBarDelegate, RemoveActionDelegate, TextCellDelegate
from desktop.app.ui.widgets.progress import ProgressSummaryWidget
from desktop.app.ui.widgets.task_table_model import ACTION_ENABLED_ROLE, TaskTableModel
from shared.contracts import TERMINAL_STATUSES, TaskRecord, TaskStatus


TASK_PANEL_DEFAULT_MIN_HEIGHT = 220
TASK_PANEL_DENSE_MIN_HEIGHT = 170
TASK_TABLE_DEFAULT_MIN_HEIGHT = 140
TASK_TABLE_DENSE_MIN_HEIGHT = 90


class TaskPanel(PanelFrame):
    start_requested = Signal()
    cancel_requested = Signal()
    cancel_queue_requested = Signal()
    remove_pending_requested = Signal()
    open_output_requested = Signal()
    open_output_dir_requested = Signal()
    copy_output_path_requested = Signal()
    remove_task_requested = Signal(str)
    zip_outputs_requested = Signal()
    copy_batch_output_paths_requested = Signal()
    open_batch_output_dir_requested = Signal()
    locate_batch_results_requested = Signal()
    task_selection_changed = Signal(str)

    def __init__(self, task_model: TaskTableModel) -> None:
        super().__init__("任务队列", density="compact")
        self._task_model = task_model
        self._busy = False
        self._start_enabled = False
        self._pending_count = 0
        self._batch_running = False
        self._zip_results_enabled = False
        self._zip_results_running = False
        self._has_recent_batch = False
        self._has_recent_batch_outputs = False
        self._dense_mode = False
        self.setObjectName("taskPanel")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(TASK_PANEL_DEFAULT_MIN_HEIGHT)
        self.setMaximumHeight(620)

        action_bar = PanelActionBar()
        self.start_button = action_bar.add_button("开始处理", role="primary")
        self.cancel_button = action_bar.add_button("取消当前", role="danger")
        self.cancel_queue_button = action_bar.add_button("取消队列", role="danger")
        self.remove_pending_button = action_bar.add_button("移除未运行", role="quiet")
        self.add_action(action_bar)

        layout = self.body_layout()

        self.total_progress = ProgressSummaryWidget()
        self.total_progress_label = self.total_progress.label
        self.total_progress_bar = self.total_progress.progress_bar
        self.start_button.clicked.connect(lambda _checked=False: self.start_requested.emit())
        self.cancel_button.clicked.connect(lambda _checked=False: self.cancel_requested.emit())
        self.cancel_queue_button.clicked.connect(lambda _checked=False: self.cancel_queue_requested.emit())
        self.remove_pending_button.clicked.connect(lambda _checked=False: self.remove_pending_requested.emit())
        layout.addWidget(self.total_progress)
        self.result_action_bar = self._create_result_action_bar()
        layout.addWidget(self.result_action_bar)
        self._sync_result_action_bar_visibility()

        self.task_table = QTableView()
        self.task_table.setObjectName("taskTable")
        self.task_table.setModel(task_model)
        self.task_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.task_table.setAlternatingRowColors(True)
        header = self.task_table.horizontalHeader()
        header.setStretchLastSection(False)
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.verticalHeader().setDefaultSectionSize(38)
        self.task_table.setShowGrid(False)
        self.task_table.setSortingEnabled(False)
        file_delegate = MediaSummaryDelegate(self.task_table)
        self.task_table.setItemDelegateForColumn(0, file_delegate)
        self.task_table.setItemDelegateForColumn(1, file_delegate)
        self.task_table.setItemDelegateForColumn(2, TextCellDelegate(self.task_table))
        self.task_table.setItemDelegateForColumn(3, ProgressBarDelegate(self.task_table))
        self.task_table.setItemDelegateForColumn(4, RemoveActionDelegate(self.task_table))
        self.task_table.resizeColumnsToContents()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.task_table.setColumnWidth(2, 190)
        self.task_table.setColumnWidth(3, 120)
        self.task_table.setColumnWidth(4, 72)
        self.task_table.verticalHeader().setDefaultSectionSize(54)
        self.task_table.setMinimumHeight(TASK_TABLE_DEFAULT_MIN_HEIGHT)
        self.task_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        layout.addWidget(self.task_table, 1)
        self.task_table.clicked.connect(self._handle_table_clicked)
        self.task_table.doubleClicked.connect(self._handle_table_double_clicked)
        self.task_table.customContextMenuRequested.connect(self._open_context_menu)
        selection_model = self.task_table.selectionModel()
        if selection_model is not None:
            selection_model.currentRowChanged.connect(self._handle_current_row_changed)

        task_model.modelReset.connect(self.refresh_total_progress)
        task_model.rowsInserted.connect(lambda *_args: self.refresh_total_progress())
        task_model.rowsRemoved.connect(lambda *_args: self.refresh_total_progress())
        task_model.dataChanged.connect(lambda *_args: self.refresh_total_progress())
        self._sync_processing_buttons()
        self.refresh_total_progress()

    def set_dense_mode(self, dense: bool) -> None:
        if dense == self._dense_mode:
            return
        self._dense_mode = dense
        self.setMinimumHeight(TASK_PANEL_DENSE_MIN_HEIGHT if dense else TASK_PANEL_DEFAULT_MIN_HEIGHT)
        self.task_table.setMinimumHeight(TASK_TABLE_DENSE_MIN_HEIGHT if dense else TASK_TABLE_DEFAULT_MIN_HEIGHT)
        self._sync_result_action_bar_visibility()
        self.updateGeometry()

    def _sync_result_action_bar_visibility(self) -> None:
        self.result_action_bar.setVisible(self._has_recent_batch and not self._dense_mode)

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._sync_processing_buttons()

    def set_start_enabled(self, enabled: bool) -> None:
        self._start_enabled = enabled
        self._sync_processing_buttons()

    def set_batch_buttons(self, pending_count: int, running: bool) -> None:
        self._pending_count = pending_count
        self._batch_running = running
        self._sync_processing_buttons()

    def set_zip_results_enabled(self, enabled: bool, *, running: bool = False) -> None:
        self._zip_results_enabled = enabled
        self._zip_results_running = running
        self._sync_zip_button_text()
        self._sync_processing_buttons()

    def set_recent_batch_results(
        self,
        summary: str,
        *,
        tooltip: str,
        has_batch: bool,
        has_successful_outputs: bool,
    ) -> None:
        self._has_recent_batch = has_batch
        self._has_recent_batch_outputs = has_successful_outputs
        self.recent_batch_summary_label.setText(summary)
        self.recent_batch_summary_label.setToolTip(tooltip)
        self.copy_batch_paths_button.setToolTip(
            "复制最近批次所有成功输出路径" if has_successful_outputs else "最近批次没有可复制的成功输出"
        )
        self.open_batch_dir_button.setToolTip(
            "打开最近批次输出目录" if has_batch else "暂无最近批次输出目录"
        )
        self.locate_batch_button.setToolTip(
            "在任务表中定位最近批次结果" if has_batch else "暂无最近批次可定位"
        )
        self._sync_zip_button_text()
        self._sync_result_action_bar_visibility()
        self._sync_processing_buttons()

    def select_task_ids(self, task_ids: set[str]) -> int:
        rows = [index for index, record in enumerate(self._task_model.records()) if record.task_id in task_ids]
        selection_model = self.task_table.selectionModel()
        if selection_model is None or not rows:
            return 0
        selection_model.clearSelection()
        for row in rows:
            selection = QItemSelection(
                self._task_model.index(row, 0),
                self._task_model.index(row, self._task_model.columnCount() - 1),
            )
            selection_model.select(
                selection,
                QItemSelectionModel.SelectionFlag.Select,
            )
        first_index = self._task_model.index(rows[0], 0)
        selection_model.setCurrentIndex(first_index, QItemSelectionModel.SelectionFlag.NoUpdate)
        self.task_table.scrollTo(first_index, QTableView.ScrollHint.PositionAtCenter)
        return len(rows)

    def refresh_total_progress(self) -> None:
        summary = _total_progress_summary(self._task_model.records())
        self.total_progress.set_summary(
            label=summary.label,
            tooltip=summary.tooltip,
            percent=summary.percent,
            indeterminate=summary.indeterminate,
            state=summary.state,
        )

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

    def selected_task_id(self) -> str | None:
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
        return records[row].task_id

    def output_path_exists(self) -> bool:
        output_path = self.selected_output_path()
        return bool(output_path and output_path.exists())

    def _handle_table_double_clicked(self, index: QModelIndex) -> None:
        if index.column() == 1 and self.output_path_exists():
            self.open_output_requested.emit()

    def _handle_table_clicked(self, index: QModelIndex) -> None:
        if index.column() != 4:
            return
        if not bool(index.data(ACTION_ENABLED_ROLE)):
            return
        records = self._task_model.records()
        if index.row() < 0 or index.row() >= len(records):
            return
        self.remove_task_requested.emit(records[index.row()].task_id)

    def _handle_current_row_changed(self, current: QModelIndex, _previous: QModelIndex) -> None:
        if not current.isValid():
            return
        records = self._task_model.records()
        if current.row() < 0 or current.row() >= len(records):
            return
        self.task_selection_changed.emit(records[current.row()].task_id)

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

    def _create_result_action_bar(self) -> QWidget:
        result_bar = QWidget()
        result_bar.setObjectName("batchResultBar")
        layout = QHBoxLayout(result_bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.recent_batch_summary_label = QLabel("最近批次：暂无结果")
        self.recent_batch_summary_label.setObjectName("recentBatchSummaryLabel")
        self.recent_batch_summary_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.recent_batch_summary_label, 1)

        self.locate_batch_button = QPushButton("定位最近批次")
        self.locate_batch_button.setProperty("role", "quiet")
        self.locate_batch_button.setProperty("density", "compact")
        self.locate_batch_button.clicked.connect(lambda _checked=False: self.locate_batch_results_requested.emit())
        layout.addWidget(self.locate_batch_button)

        self.copy_batch_paths_button = QPushButton("复制成功路径")
        self.copy_batch_paths_button.setProperty("role", "quiet")
        self.copy_batch_paths_button.setProperty("density", "compact")
        self.copy_batch_paths_button.clicked.connect(lambda _checked=False: self.copy_batch_output_paths_requested.emit())
        layout.addWidget(self.copy_batch_paths_button)

        self.open_batch_dir_button = QPushButton("打开输出目录")
        self.open_batch_dir_button.setProperty("role", "quiet")
        self.open_batch_dir_button.setProperty("density", "compact")
        self.open_batch_dir_button.clicked.connect(lambda _checked=False: self.open_batch_output_dir_requested.emit())
        layout.addWidget(self.open_batch_dir_button)

        self.zip_results_button = QPushButton("无批次可打包")
        self.zip_results_button.setProperty("role", "result")
        self.zip_results_button.setProperty("density", "compact")
        self.zip_results_button.clicked.connect(lambda _checked=False: self.zip_outputs_requested.emit())
        layout.addWidget(self.zip_results_button)
        return result_bar

    def _sync_zip_button_text(self) -> None:
        if self._zip_results_running:
            text = "正在打包..."
            tooltip = "正在打包最近批次成功结果"
        elif not self._has_recent_batch:
            text = "无批次可打包"
            tooltip = "完成一次批处理后可打包成功结果"
        elif not self._has_recent_batch_outputs:
            text = "无成功结果"
            tooltip = "最近批次没有存在的成功输出文件"
        else:
            text = "打包成功结果"
            tooltip = "打包最近批次所有成功输出文件"
        self.zip_results_button.setText(text)
        self.zip_results_button.setToolTip(tooltip)

    def _sync_processing_buttons(self) -> None:
        self.start_button.setEnabled(self._start_enabled and not self._busy)
        self.cancel_button.setEnabled(self._busy)
        self.cancel_queue_button.setEnabled(self._batch_running)
        self.remove_pending_button.setEnabled(self._pending_count > 0 and not self._batch_running and not self._busy)
        result_actions_enabled = self._has_recent_batch and not self._batch_running and not self._busy
        self.locate_batch_button.setEnabled(result_actions_enabled)
        self.open_batch_dir_button.setEnabled(result_actions_enabled)
        self.copy_batch_paths_button.setEnabled(result_actions_enabled and self._has_recent_batch_outputs)
        self.zip_results_button.setEnabled(
            self._zip_results_enabled
            and self._has_recent_batch_outputs
            and not self._zip_results_running
            and not self._batch_running
            and not self._busy
        )


class _TotalProgressSummary:
    def __init__(
        self,
        *,
        label: str,
        tooltip: str,
        percent: int,
        indeterminate: bool = False,
        state: str = "active",
    ) -> None:
        self.label = label
        self.tooltip = tooltip
        self.percent = percent
        self.indeterminate = indeterminate
        self.state = state


def _total_progress_summary(records: list[TaskRecord]) -> _TotalProgressSummary:
    total = len(records)
    if total == 0:
        return _TotalProgressSummary(label="无任务", tooltip="当前没有任务", percent=0, state="empty")

    done = sum(1 for record in records if record.status in TERMINAL_STATUSES)
    if any(record.status is TaskStatus.running and record.progress is None for record in records):
        return _TotalProgressSummary(
            label=f"总进度 {done}/{total} · 运行中",
            tooltip=f"总进度：{done}/{total}，当前任务无法估算精确百分比",
            percent=0,
            indeterminate=True,
            state="running",
        )

    progress_total = sum(_record_progress_value(record) for record in records)
    percent = max(0, min(100, int(round(progress_total / total * 100))))
    label = f"总进度 {done}/{total} · {percent}%"
    tooltip = f"总进度：{done}/{total}，{percent}%"
    return _TotalProgressSummary(
        label=label,
        tooltip=tooltip,
        percent=percent,
        state=_total_progress_state(records, percent),
    )


def _record_progress_value(record: TaskRecord) -> float:
    if record.status in TERMINAL_STATUSES:
        return 1.0
    if isinstance(record.progress, (int, float)):
        return max(0.0, min(float(record.progress), 1.0))
    return 0.0


def _total_progress_state(records: list[TaskRecord], percent: int) -> str:
    if any(record.status is TaskStatus.running for record in records):
        return "running"
    if any(record.status is TaskStatus.failed for record in records):
        return "failure"
    if any(record.status is TaskStatus.cancelled for record in records):
        return "cancelled"
    if percent >= 100:
        return "success"
    return "active"
