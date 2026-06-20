from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QCloseEvent, QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from desktop.app.core.constants import WINDOW_TITLE
from desktop.app.runtime.binaries import RuntimeHealth
from desktop.app.ui.panels import OperationPanel, RuntimePanel, StatusPanel, TaskPanel
from desktop.app.ui.widgets.task_table_model import TaskTableModel
from shared.contracts import MediaInfo


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
        self._last_output_path: Path | None = None
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(1280, 840)
        self.setMinimumSize(1080, 760)

        central = QWidget()
        central.setObjectName("appRoot")
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(14)

        self.runtime_panel = RuntimePanel()
        self.operation_panel = OperationPanel()
        self.status_panel = StatusPanel()
        self.task_panel = TaskPanel(task_model)
        self._connect_panel_signals()

        root.addWidget(self._create_masthead())

        runtime_scroll = QScrollArea()
        runtime_scroll.setObjectName("runtimeScroll")
        runtime_scroll.setFrameShape(QFrame.Shape.NoFrame)
        runtime_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        runtime_scroll.setWidgetResizable(True)
        runtime_scroll.setWidget(self.runtime_panel)

        operation_scroll = QScrollArea()
        operation_scroll.setObjectName("operationScroll")
        operation_scroll.setFrameShape(QFrame.Shape.NoFrame)
        operation_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        operation_scroll.setWidgetResizable(True)
        operation_scroll.setWidget(self.operation_panel)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(10)
        splitter.addWidget(runtime_scroll)
        splitter.addWidget(operation_scroll)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([520, 700])
        root.addWidget(splitter, 1)

        root.addWidget(self.status_panel)
        root.addWidget(self.task_panel)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Ready")

    def set_initial_paths(self, *, ffmpeg_bin: str, ffprobe_bin: str, output_dir: Path) -> None:
        self.runtime_panel.set_initial_paths(ffmpeg_bin=ffmpeg_bin, ffprobe_bin=ffprobe_bin, output_dir=output_dir)

    def selected_ffmpeg_bin(self) -> str:
        return self.runtime_panel.selected_ffmpeg_bin()

    def selected_ffprobe_bin(self) -> str:
        return self.runtime_panel.selected_ffprobe_bin()

    def selected_input_path(self) -> Path | None:
        return self.runtime_panel.selected_input_path()

    def selected_output_dir(self) -> Path | None:
        return self.runtime_panel.selected_output_dir()

    def set_runtime_health(self, health: RuntimeHealth) -> None:
        version = self.runtime_panel.set_runtime_health(health)
        if version:
            self.statusBar().showMessage(version)

    def set_media_info(self, media_info: MediaInfo | None) -> None:
        self.status_panel.set_media_info(media_info)
        if media_info is not None:
            self.operation_panel.apply_media_defaults(media_info)

    def apply_media_defaults_to_form(self, media_info: MediaInfo | None) -> None:
        if media_info is None:
            return
        self.operation_panel.apply_media_defaults(media_info)

    def set_busy(self, busy: bool) -> None:
        self.runtime_panel.set_busy(busy)
        self.operation_panel.set_busy(busy)
        if busy:
            self.status_panel.set_result_buttons_enabled(False)

    def set_start_enabled(self, enabled: bool) -> None:
        busy = self.operation_panel.is_busy()
        effective_enabled = enabled and not busy
        self.operation_panel.set_start_enabled(effective_enabled)
        self.runtime_panel.set_batch_add_enabled(effective_enabled)

    def set_batch_progress(self, current: int, total: int) -> None:
        self.runtime_panel.set_batch_progress(current, total)

    def set_batch_buttons(self, pending_count: int, running: bool) -> None:
        self.operation_panel.set_batch_buttons(pending_count=pending_count, running=running)

    def set_progress(self, progress: float | None) -> None:
        self.status_panel.set_progress(progress)

    def reset_progress(self) -> None:
        self.status_panel.reset_progress()

    def append_log(self, line: str) -> None:
        self.status_panel.append_log(line)

    def clear_log(self) -> None:
        self.status_panel.clear_log()

    def set_current_output(self, output_path: Path | None) -> None:
        self._last_output_path = output_path
        self.status_panel.set_current_output(output_path)
        self.status_panel.set_result_buttons_enabled(bool(output_path and output_path.exists()))

    def current_output_path(self) -> Path | None:
        return self._last_output_path

    def set_stack_mode(self, enabled: bool) -> None:
        self.operation_panel.set_stack_mode(enabled)

    def stack_mode(self) -> bool:
        return self.operation_panel.stack_mode()

    def set_stack_items(self, items: list[str]) -> None:
        self.operation_panel.set_stack_items(items)

    def refresh_stack_controls(self) -> None:
        self.operation_panel.refresh_stack_controls()

    def _update_stack_add_enabled(self) -> None:
        self.refresh_stack_controls()

    def set_command_preview(self, command: str) -> None:
        self.status_panel.set_command_preview(command)

    def set_output_estimate(self, estimate: str) -> None:
        self.status_panel.set_output_estimate(estimate)

    def selected_operation_payload(self):
        return self.operation_panel.selected_operation_payload()

    def show_error(self, message: str) -> None:
        self.statusBar().showMessage(message)
        QMessageBox.warning(self, "错误", message)

    def show_status(self, message: str) -> None:
        self.statusBar().showMessage(message)

    def choose_input_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择媒体文件")
        if not path:
            return
        self.runtime_panel.set_input_path_text(path)
        self.input_file_selected.emit(path)

    def choose_batch_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "添加批处理文件", self.runtime_panel.input_path_text())
        if not paths:
            return
        self.batch_files_selected.emit(paths)

    def choose_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择输出目录", str(self.selected_output_dir() or ""))
        if not path:
            return
        self.runtime_panel.set_output_dir_text(path)
        self.output_dir_selected.emit(path)

    def choose_operation_file(self, field_name: str, file_filter: str) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择文件", "", file_filter)
        if path:
            self.operation_panel.set_file_path(field_name, path)

    def choose_subtitle_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择字幕文件", "", "Subtitles (*.srt *.vtt *.ass *.ssa)")
        if path:
            self.operation_panel.set_subtitle_path(path)

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

    def _connect_panel_signals(self) -> None:
        self.runtime_panel.input_browse_requested.connect(self.choose_input_file)
        self.runtime_panel.input_path_dropped.connect(self.input_file_selected.emit)
        self.runtime_panel.batch_files_requested.connect(self.choose_batch_files)
        self.runtime_panel.output_dir_requested.connect(self.choose_output_dir)
        self.runtime_panel.refresh_requested.connect(self.refresh_requested.emit)

        self.operation_panel.file_browse_requested.connect(self.choose_operation_file)
        self.operation_panel.start_requested.connect(self.start_requested.emit)
        self.operation_panel.cancel_requested.connect(self.cancel_requested.emit)
        self.operation_panel.cancel_queue_requested.connect(self.cancel_queue_requested.emit)
        self.operation_panel.remove_pending_requested.connect(self.remove_pending_requested.emit)
        self.operation_panel.stack_mode_toggled.connect(self.stack_mode_toggled.emit)
        self.operation_panel.stack_add_requested.connect(self.stack_add_requested.emit)
        self.operation_panel.stack_move_up_requested.connect(self.stack_move_up_requested.emit)
        self.operation_panel.stack_move_down_requested.connect(self.stack_move_down_requested.emit)
        self.operation_panel.stack_remove_requested.connect(self.stack_remove_requested.emit)
        self.operation_panel.stack_clear_requested.connect(self.stack_clear_requested.emit)
        self.operation_panel.command_preview_requested.connect(self.command_preview_requested.emit)

        self.status_panel.open_output_requested.connect(self.open_output_requested.emit)
        self.status_panel.open_output_dir_requested.connect(self.open_output_dir_requested.emit)
        self.status_panel.copy_output_path_requested.connect(self.copy_output_path_requested.emit)

    def _create_masthead(self) -> QFrame:
        masthead = QFrame()
        masthead.setObjectName("masthead")
        layout = QHBoxLayout(masthead)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        title = QLabel("ffmpeg GUI")
        title.setObjectName("appTitle")
        offline_badge = QLabel("offline-first")
        offline_badge.setProperty("role", "badge")
        local_badge = QLabel("本机处理 · 不上传")
        local_badge.setProperty("role", "successBadge")

        layout.addWidget(title)
        layout.addWidget(offline_badge)
        layout.addWidget(local_badge)
        layout.addStretch(1)
        return masthead
