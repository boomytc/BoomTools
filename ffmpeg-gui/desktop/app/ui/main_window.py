from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
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
from shared.contracts import MediaInfo, TaskRecord


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
    closing = Signal()

    def __init__(self, task_model: TaskTableModel) -> None:
        super().__init__()
        self.task_model = task_model
        self._last_output_path: Path | None = None
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
        layout.addWidget(self.operation_form, 1)

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
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setReadOnly(True)
        result_row = QHBoxLayout()
        self.open_output_button = QPushButton("打开输出文件")
        self.open_output_dir_button = QPushButton("打开输出目录")
        self.open_output_button.clicked.connect(self.open_output_requested.emit)
        self.open_output_dir_button.clicked.connect(self.open_output_dir_requested.emit)
        result_row.addWidget(self.open_output_button)
        result_row.addWidget(self.open_output_dir_button)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.output_path_edit)
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
