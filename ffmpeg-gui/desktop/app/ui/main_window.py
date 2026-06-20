from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QCloseEvent, QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QRadioButton,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from desktop.app.core.constants import WINDOW_TITLE
from desktop.app.runtime.binaries import RuntimeHealth
from desktop.app.ui.widgets.operation_form import OperationFormWidget
from desktop.app.ui.widgets.task_table_model import TaskTableModel
from shared.contracts import MediaInfo, Operation, TaskRecord


STACK_FILTER_OPERATIONS = {
    Operation.resize_compress,
    Operation.crop,
    Operation.rotate,
    Operation.adjust,
    Operation.denoise,
    Operation.sharpen_blur,
    Operation.pad,
    Operation.volume,
    Operation.speed,
    Operation.fade,
}


class MainWindow(QMainWindow):
    input_file_selected = Signal(str)
    batch_files_selected = Signal(list)
    output_dir_selected = Signal(str)
    refresh_requested = Signal()
    start_requested = Signal()
    cancel_requested = Signal()
    cancel_queue_requested = Signal()
    remove_pending_requested = Signal()
    open_output_requested = Signal()
    open_output_dir_requested = Signal()
    stack_mode_toggled = Signal(bool)
    stack_add_requested = Signal()
    stack_move_up_requested = Signal(int)
    stack_move_down_requested = Signal(int)
    stack_remove_requested = Signal(int)
    stack_clear_requested = Signal()
    command_preview_requested = Signal()
    copy_output_path_requested = Signal()
    closing = Signal()

    def __init__(self, task_model: TaskTableModel) -> None:
        super().__init__()
        self.task_model = task_model
        self._last_output_path: Path | None = None
        self._stack_items: list[str] = []
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(1180, 760)
        self.setMinimumSize(960, 620)

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        root.addWidget(self._build_runtime_panel())

        splitter = QSplitter()
        splitter.addWidget(self._build_operation_panel())
        splitter.addWidget(self._build_status_panel())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([430, 720])
        root.addWidget(splitter, 1)

        root.addWidget(self._build_task_panel())
        self.setCentralWidget(central)
        self.statusBar().showMessage("Ready")
        self._set_result_buttons_enabled(False)

    def set_initial_paths(self, *, ffmpeg_bin: str, ffprobe_bin: str, output_dir: Path) -> None:
        self.ffmpeg_bin_edit.setText(ffmpeg_bin)
        self.ffprobe_bin_edit.setText(ffprobe_bin)
        self.output_dir_edit.setText(str(output_dir))

    def selected_ffmpeg_bin(self) -> str:
        return self.ffmpeg_bin_edit.text().strip() or "ffmpeg"

    def selected_ffprobe_bin(self) -> str:
        return self.ffprobe_bin_edit.text().strip() or "ffprobe"

    def selected_input_path(self) -> Path | None:
        text = self.input_path_edit.text().strip()
        return Path(text) if text else None

    def selected_output_dir(self) -> Path | None:
        text = self.output_dir_edit.text().strip()
        return Path(text) if text else None

    def set_runtime_health(self, health: RuntimeHealth) -> None:
        if health.ok:
            label = f"ffmpeg/ffprobe 可用：{health.ffmpeg_path or self.selected_ffmpeg_bin()}"
            self.health_label.setProperty("state", "ok")
        else:
            missing = []
            if not health.ffmpeg_available:
                missing.append("ffmpeg")
            if not health.ffprobe_available:
                missing.append("ffprobe")
            label = "不可用：" + ", ".join(missing)
            self.health_label.setProperty("state", "error")
        self.health_label.setText(label)
        self.health_label.style().unpolish(self.health_label)
        self.health_label.style().polish(self.health_label)
        if health.ffmpeg_version:
            self.statusBar().showMessage(health.ffmpeg_version)

    def set_media_info(self, media_info: MediaInfo | None) -> None:
        if media_info is None:
            self.media_info_view.setPlainText("请选择本机媒体文件。")
            return
        self.media_info_view.setPlainText(json.dumps(media_info.raw, ensure_ascii=False, indent=2))
        self.operation_form.apply_media_defaults(media_info)

    def apply_media_defaults_to_form(self, media_info: MediaInfo | None) -> None:
        if media_info is None:
            return
        self.operation_form.apply_media_defaults(media_info)

    def set_busy(self, busy: bool) -> None:
        self.start_button.setEnabled(not busy)
        self.cancel_button.setEnabled(busy)
        self.operation_form.set_enabled(not busy)
        self.input_browse_button.setEnabled(not busy)
        self.batch_add_button.setEnabled(not busy)
        self.output_browse_button.setEnabled(not busy)
        self.refresh_button.setEnabled(not busy)
        self.remove_pending_button.setEnabled(not busy)
        self.cancel_queue_button.setEnabled(busy)
        self.single_mode_radio.setEnabled(not busy)
        self.stack_mode_radio.setEnabled(not busy)
        self.stack_add_button.setEnabled(False)
        self._set_stack_actions_enabled(not busy and len(self._stack_items) > 0)
        self.stack_list.setEnabled(not busy)
        self._update_stack_add_enabled()
        if busy:
            self._set_result_buttons_enabled(False)

    def set_start_enabled(self, enabled: bool) -> None:
        busy = self.cancel_button.isEnabled()
        self.start_button.setEnabled(enabled and not busy)
        self.batch_add_button.setEnabled(enabled and not busy)

    def set_batch_progress(self, current: int, total: int) -> None:
        if total == 0:
            self.batch_progress_label.setText("批处理：未启动")
            return
        self.batch_progress_label.setText(f"批处理：{current}/{total}")

    def set_batch_buttons(self, pending_count: int, running: bool) -> None:
        self.remove_pending_button.setEnabled(pending_count > 0 and not running)
        self.cancel_queue_button.setEnabled(running)

    def set_progress(self, progress: float | None) -> None:
        if progress is None:
            self.progress_bar.setRange(0, 0)
            self.progress_bar.setFormat("运行中")
            return
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(int(progress * 100))
        self.progress_bar.setFormat("%p%")

    def reset_progress(self) -> None:
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")

    def append_log(self, line: str) -> None:
        self.log_view.appendPlainText(line)

    def clear_log(self) -> None:
        self.log_view.clear()

    def set_current_output(self, output_path: Path | None) -> None:
        self._last_output_path = output_path
        self.output_path_edit.setText(str(output_path) if output_path else "")
        self._set_result_buttons_enabled(bool(output_path and output_path.exists()))

    def current_output_path(self) -> Path | None:
        return self._last_output_path

    def set_stack_mode(self, enabled: bool) -> None:
        self.stack_mode_radio.setChecked(enabled)
        self.single_mode_radio.setChecked(not enabled)
        self.stack_container.setVisible(enabled)
        self._update_stack_add_enabled()
        self._set_stack_actions_enabled(bool(self._stack_items))
        self._set_stack_note_by_operation()

    def stack_mode(self) -> bool:
        return self.stack_mode_radio.isChecked()

    def set_stack_items(self, items: list[str]) -> None:
        self._stack_items = list(items)
        self.stack_list.clear()
        for item in items:
            QListWidgetItem(item, self.stack_list)
        self.stack_list_label.setText(f"Stack 队列：{len(items)}项")
        self._set_stack_actions_enabled(len(items) > 0)
        self._set_stack_note_by_operation()

    def set_command_preview(self, command: str) -> None:
        self.command_preview.setPlainText(command)

    def set_output_estimate(self, estimate: str) -> None:
        self.output_estimate_label.setText(estimate)

    def selected_operation_payload(self):
        return self.operation_form.collect()

    def show_error(self, message: str) -> None:
        self.statusBar().showMessage(message)
        QMessageBox.warning(self, "错误", message)

    def show_status(self, message: str) -> None:
        self.statusBar().showMessage(message)

    def choose_input_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择媒体文件")
        if not path:
            return
        self.input_path_edit.setText(path)
        self.input_file_selected.emit(path)

    def choose_batch_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "添加批处理文件", self.input_path_edit.text())
        if not paths:
            return
        self.batch_files_selected.emit(paths)

    def choose_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择输出目录", self.output_dir_edit.text())
        if not path:
            return
        self.output_dir_edit.setText(path)
        self.output_dir_selected.emit(path)

    def choose_operation_file(self, field_name: str, file_filter: str) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择文件", "", file_filter)
        if path:
            self.operation_form.set_file_path(field_name, path)

    def choose_subtitle_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择字幕文件", "", "Subtitles (*.srt *.vtt *.ass *.ssa)")
        if path:
            self.operation_form.set_subtitle_path(path)

    def open_output(self) -> None:
        if self._last_output_path and self._last_output_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_output_path)))

    def open_output_dir(self) -> None:
        if self._last_output_path:
            directory = self._last_output_path.parent
        else:
            directory = self.selected_output_dir()
        if directory and directory.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory)))

    def copy_output_path(self) -> None:
        if not self._last_output_path:
            self.show_status("当前无可复制的输出路径")
            return
        QGuiApplication.clipboard().setText(str(self._last_output_path))
        self.show_status("已复制输出路径到剪贴板")

    def closeEvent(self, event: QCloseEvent) -> None:
        self.closing.emit()
        super().closeEvent(event)

    def _build_runtime_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("topPanel")
        layout = QGridLayout(panel)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)

        self.input_path_edit = QLineEdit()
        self.input_path_edit.setPlaceholderText("选择本机媒体文件")
        self.input_browse_button = QPushButton("选择文件")
        self.input_browse_button.clicked.connect(self.choose_input_file)

        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("输出目录，默认 data/outputs")
        self.output_browse_button = QPushButton("输出目录")
        self.output_browse_button.clicked.connect(self.choose_output_dir)

        self.ffmpeg_bin_edit = QLineEdit()
        self.ffmpeg_bin_edit.setPlaceholderText("ffmpeg")
        self.ffprobe_bin_edit = QLineEdit()
        self.ffprobe_bin_edit.setPlaceholderText("ffprobe")
        self.refresh_button = QPushButton("检查")
        self.refresh_button.clicked.connect(self.refresh_requested.emit)

        self.health_label = QLabel("等待检查 ffmpeg/ffprobe")
        self.health_label.setObjectName("healthLabel")
        self.batch_progress_label = QLabel("批处理：未启动")
        self.batch_add_button = QPushButton("添加多个文件到队列")
        self.batch_add_button.clicked.connect(self.choose_batch_files)

        layout.addWidget(QLabel("输入"), 0, 0)
        layout.addWidget(self.input_path_edit, 0, 1, 1, 3)
        layout.addWidget(self.input_browse_button, 0, 4)
        layout.addWidget(self.batch_add_button, 0, 5)
        layout.addWidget(QLabel("输出"), 1, 0)
        layout.addWidget(self.output_dir_edit, 1, 1, 1, 3)
        layout.addWidget(self.output_browse_button, 1, 4)
        layout.addWidget(QLabel("ffmpeg"), 2, 0)
        layout.addWidget(self.ffmpeg_bin_edit, 2, 1)
        layout.addWidget(QLabel("ffprobe"), 2, 2)
        layout.addWidget(self.ffprobe_bin_edit, 2, 3)
        layout.addWidget(self.refresh_button, 2, 4)
        layout.addWidget(self.health_label, 3, 0, 1, 5)
        layout.addWidget(self.batch_progress_label, 4, 0, 1, 5)
        layout.setColumnStretch(1, 2)
        layout.setColumnStretch(3, 2)
        return panel

    def _build_operation_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self.operation_form = OperationFormWidget()
        self.operation_form.file_browse_requested.connect(self.choose_operation_file)
        self.operation_form.spec_changed.connect(self._update_stack_add_enabled)
        self.operation_form.spec_changed.connect(self.command_preview_requested.emit)
        layout.addWidget(self.operation_form, 1)

        mode_row = QHBoxLayout()
        self.single_mode_radio = QRadioButton("单操作")
        self.stack_mode_radio = QRadioButton("Stack")
        self.single_mode_radio.setChecked(True)
        mode_row.addWidget(self.single_mode_radio)
        mode_row.addWidget(self.stack_mode_radio)
        mode_row.addStretch(1)
        layout.addLayout(mode_row)

        self.single_mode_radio.toggled.connect(lambda checked: self.stack_mode_toggled.emit(False) if checked else None)
        self.stack_mode_radio.toggled.connect(lambda checked: self.stack_mode_toggled.emit(True) if checked else None)

        button_row = QHBoxLayout()
        self.start_button = QPushButton("开始处理")
        self.start_button.setObjectName("primaryButton")
        self.cancel_button = QPushButton("取消当前")
        self.cancel_queue_button = QPushButton("取消队列")
        self.remove_pending_button = QPushButton("移除未运行")
        self.cancel_button.setEnabled(False)
        self.cancel_queue_button.setEnabled(False)
        self.remove_pending_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_requested.emit)
        self.cancel_button.clicked.connect(self.cancel_requested.emit)
        self.cancel_queue_button.clicked.connect(self.cancel_queue_requested.emit)
        self.remove_pending_button.clicked.connect(self.remove_pending_requested.emit)
        button_row.addWidget(self.start_button)
        button_row.addWidget(self.cancel_button)
        button_row.addWidget(self.cancel_queue_button)
        button_row.addWidget(self.remove_pending_button)
        layout.addLayout(button_row)

        self.stack_container = QGroupBox("Stack 队列")
        stack_layout = QVBoxLayout(self.stack_container)
        self.stack_mode_label = QLabel("说明：仅支持可链式单输入滤镜，顺序即执行顺序。")
        stack_layout.addWidget(self.stack_mode_label)

        self.stack_list_label = QLabel("Stack 队列：0项")
        self.stack_list = QListWidget()
        self.stack_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        stack_buttons = QHBoxLayout()
        self.stack_add_button = QPushButton("添加当前操作到 Stack")
        self.stack_move_up_button = QPushButton("上移")
        self.stack_move_down_button = QPushButton("下移")
        self.stack_remove_button = QPushButton("移除")
        self.stack_clear_button = QPushButton("清空")
        self.stack_add_button.clicked.connect(self.stack_add_requested.emit)
        self.stack_move_up_button.clicked.connect(self._emit_stack_move_up)
        self.stack_move_down_button.clicked.connect(self._emit_stack_move_down)
        self.stack_remove_button.clicked.connect(self._emit_stack_remove)
        self.stack_clear_button.clicked.connect(self.stack_clear_requested.emit)
        stack_buttons.addWidget(self.stack_add_button)
        stack_buttons.addWidget(self.stack_move_up_button)
        stack_buttons.addWidget(self.stack_move_down_button)
        stack_buttons.addWidget(self.stack_remove_button)
        stack_buttons.addWidget(self.stack_clear_button)

        stack_layout.addWidget(self.stack_list_label)
        stack_layout.addWidget(self.stack_list)
        stack_layout.addLayout(stack_buttons)
        stack_layout.addWidget(QLabel("说明：切换操作后可继续补充栈项，保存顺序即执行顺序。"))
        self.stack_container.setVisible(False)
        layout.addWidget(self.stack_container)

        return panel

    def _build_status_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        media_group = QGroupBox("媒体信息")
        media_layout = QVBoxLayout(media_group)
        self.media_info_view = QPlainTextEdit()
        self.media_info_view.setReadOnly(True)
        self.media_info_view.setPlainText("请选择本机媒体文件。")
        media_layout.addWidget(self.media_info_view)
        layout.addWidget(media_group, 2)

        progress_group = QGroupBox("任务进度")
        progress_layout = QVBoxLayout(progress_group)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.output_estimate_label = QLabel("输出大小保守估算：等待参数")
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setReadOnly(True)
        self.command_preview = QPlainTextEdit()
        self.command_preview.setReadOnly(True)
        self.command_preview.setFixedHeight(120)
        result_row = QHBoxLayout()
        self.open_output_button = QPushButton("打开输出文件")
        self.open_output_dir_button = QPushButton("打开输出目录")
        self.copy_output_path_button = QPushButton("复制输出路径")
        self.open_output_button.clicked.connect(self.open_output_requested.emit)
        self.open_output_dir_button.clicked.connect(self.open_output_dir_requested.emit)
        self.copy_output_path_button.clicked.connect(self.copy_output_path_requested.emit)
        result_row.addWidget(self.open_output_button)
        result_row.addWidget(self.open_output_dir_button)
        result_row.addWidget(self.copy_output_path_button)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.output_path_edit)
        progress_layout.addWidget(self.output_estimate_label)
        progress_layout.addWidget(QLabel("命令预览"))
        progress_layout.addWidget(self.command_preview)
        progress_layout.addLayout(result_row)
        layout.addWidget(progress_group)

        log_group = QGroupBox("日志")
        log_layout = QVBoxLayout(log_group)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        log_layout.addWidget(self.log_view)
        layout.addWidget(log_group, 2)
        return panel

    def _build_task_panel(self) -> QWidget:
        group = QGroupBox("任务")
        layout = QVBoxLayout(group)
        self.task_table = QTableView()
        self.task_table.setModel(self.task_model)
        self.task_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.horizontalHeader().setStretchLastSection(True)
        self.task_table.resizeColumnsToContents()
        layout.addWidget(self.task_table)
        return group

    def _set_result_buttons_enabled(self, enabled: bool) -> None:
        self.open_output_button.setEnabled(enabled)
        self.open_output_dir_button.setEnabled(enabled)
        self.copy_output_path_button.setEnabled(enabled)

    def _update_stack_add_enabled(self) -> None:
        if not hasattr(self, "stack_add_button"):
            return
        self.stack_add_button.setEnabled(self.stack_mode() and self._is_stack_operation_supported())
        self._set_stack_note_by_operation()

    def _is_stack_operation_supported(self) -> bool:
        return self.operation_form.selected_operation() in STACK_FILTER_OPERATIONS

    def _set_stack_note_by_operation(self) -> None:
        if not self.stack_mode():
            return
        if self._is_stack_operation_supported():
            self.stack_mode_label.setText("说明：当前操作支持加入 Stack。")
            return
        self.stack_mode_label.setText("说明：当前操作不支持加入 Stack。")

    def _emit_stack_move_up(self) -> None:
        index = self._selected_stack_index()
        if index is not None and index > 0:
            self.stack_move_up_requested.emit(index)

    def _emit_stack_move_down(self) -> None:
        index = self._selected_stack_index()
        if index is not None and index < self.stack_list.count() - 1:
            self.stack_move_down_requested.emit(index)

    def _emit_stack_remove(self) -> None:
        index = self._selected_stack_index()
        if index is not None:
            self.stack_remove_requested.emit(index)

    def _selected_stack_index(self) -> int | None:
        item = self.stack_list.currentItem()
        if item is None:
            return None
        return self.stack_list.row(item)

    def _set_stack_actions_enabled(self, has_items: bool) -> None:
        busy = self.cancel_button.isEnabled()
        has_items = has_items and not busy
        self.stack_move_up_button.setEnabled(has_items)
        self.stack_move_down_button.setEnabled(has_items)
        self.stack_remove_button.setEnabled(has_items)
        self.stack_clear_button.setEnabled(has_items)
