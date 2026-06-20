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
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from desktop.app.core.constants import WINDOW_TITLE
from desktop.app.runtime.binaries import RuntimeHealth
from desktop.app.ui.dialogs import LogDialog, SettingsDialog
from desktop.app.ui.panels import OperationPanel, RuntimePanel, StatusPanel, TaskPanel
from desktop.app.ui.widgets.task_table_model import TaskTableModel
from shared.contracts import BATCH_SUPPORTED_OPERATIONS, MediaInfo


class MainWindow(QMainWindow):
    input_file_selected = Signal(str)
    input_mode_changed = Signal(bool)
    batch_files_selected = Signal(list)
    batch_files_cleared = Signal()
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
        self._log_has_content = False
        self._log_has_error = False
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(1280, 900)
        self.setMinimumSize(1080, 860)

        central = QWidget()
        central.setObjectName("appRoot")
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(14)

        self.runtime_panel = RuntimePanel()
        self.operation_panel = OperationPanel()
        self.status_panel = StatusPanel()
        self.task_panel = TaskPanel(task_model)
        self.settings_dialog = SettingsDialog(self)
        self.log_dialog = LogDialog(self)
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
        self.settings_dialog.set_initial_paths(ffmpeg_bin=ffmpeg_bin, ffprobe_bin=ffprobe_bin)
        self.status_panel.set_output_dir_text(str(output_dir))

    def selected_ffmpeg_bin(self) -> str:
        return self.settings_dialog.selected_ffmpeg_bin()

    def selected_ffprobe_bin(self) -> str:
        return self.settings_dialog.selected_ffprobe_bin()

    def selected_input_path(self) -> Path | None:
        return self.runtime_panel.selected_input_path()

    def selected_batch_paths(self) -> list[Path]:
        return self.runtime_panel.selected_batch_paths()

    def batch_input_mode(self) -> bool:
        return self.runtime_panel.batch_input_mode()

    def selected_output_dir(self) -> Path | None:
        return self.status_panel.selected_output_dir()

    def set_runtime_health(self, health: RuntimeHealth) -> None:
        version = self.settings_dialog.set_runtime_health(health)
        self._set_settings_button_health(health)
        if version:
            self.statusBar().showMessage(version)

    def set_media_info(self, media_info: MediaInfo | None) -> None:
        self.runtime_panel.set_media_info(media_info)
        if media_info is not None:
            self.operation_panel.apply_media_defaults(media_info)

    def apply_media_defaults_to_form(self, media_info: MediaInfo | None) -> None:
        if media_info is None:
            return
        self.operation_panel.apply_media_defaults(media_info)

    def set_busy(self, busy: bool) -> None:
        self.runtime_panel.set_busy(busy)
        self.operation_panel.set_busy(busy)
        self.settings_dialog.set_busy(busy)
        self.status_panel.set_busy(busy)
        if busy:
            self.status_panel.set_result_buttons_enabled(False)

    def set_start_enabled(self, enabled: bool) -> None:
        busy = self.operation_panel.is_busy()
        effective_enabled = enabled and not busy
        self.operation_panel.set_start_enabled(effective_enabled)

    def set_batch_progress(self, current: int, total: int) -> None:
        self.runtime_panel.set_batch_progress(current, total)

    def set_batch_buttons(self, pending_count: int, running: bool) -> None:
        self.operation_panel.set_batch_buttons(pending_count=pending_count, running=running)

    def set_progress(self, progress: float | None) -> None:
        self.status_panel.set_progress(progress)

    def reset_progress(self) -> None:
        self.status_panel.reset_progress()

    def append_log(self, line: str) -> None:
        self.log_dialog.append_log(line)
        self._log_has_content = True
        if "ERROR" in line.upper():
            self._log_has_error = True
        self._refresh_log_button()

    def clear_log(self) -> None:
        self.log_dialog.clear_log()

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

    def set_batch_input_mode(self, enabled: bool) -> None:
        self.runtime_panel.set_batch_input_mode(enabled, emit=False)
        self.operation_panel.set_batch_input_mode(enabled, BATCH_SUPPORTED_OPERATIONS)

    def set_batch_input_paths(self, paths: list[str | Path]) -> None:
        self.runtime_panel.set_batch_paths(paths)

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
        self.set_batch_input_mode(False)
        self.runtime_panel.set_input_path_text(path)
        self.input_file_selected.emit(path)

    def choose_batch_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "添加批处理文件", self.runtime_panel.input_path_text())
        if not paths:
            return
        self.set_batch_input_mode(True)
        self.runtime_panel.set_batch_paths(paths)
        self.batch_files_selected.emit(paths)

    def choose_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择输出目录", str(self.selected_output_dir() or ""))
        if not path:
            return
        self.status_panel.set_output_dir_text(path)
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

    def open_settings_dialog(self) -> None:
        self.settings_dialog.open()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def open_log_dialog(self) -> None:
        self.log_dialog.open()
        self.log_dialog.raise_()
        self.log_dialog.activateWindow()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.closing.emit()
        super().closeEvent(event)

    def _connect_panel_signals(self) -> None:
        self.runtime_panel.input_browse_requested.connect(self.choose_input_file)
        self.runtime_panel.input_path_dropped.connect(self.input_file_selected.emit)
        self.runtime_panel.input_mode_changed.connect(self._on_input_mode_changed)
        self.runtime_panel.batch_files_requested.connect(self.choose_batch_files)
        self.runtime_panel.batch_paths_dropped.connect(self.batch_files_selected.emit)
        self.runtime_panel.batch_files_cleared.connect(self.batch_files_cleared.emit)
        self.status_panel.output_dir_requested.connect(self.choose_output_dir)
        self.settings_dialog.check_requested.connect(self.refresh_requested.emit)

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
        self.log_dialog.cleared.connect(self._mark_log_cleared)

    def _on_input_mode_changed(self, batch_mode: bool) -> None:
        self.operation_panel.set_batch_input_mode(batch_mode, BATCH_SUPPORTED_OPERATIONS)
        self.input_mode_changed.emit(batch_mode)

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
        self.log_button = QToolButton()
        self.log_button.setObjectName("logButton")
        self.log_button.setText("▤")
        self.log_button.setAccessibleName("FFmpeg Log")
        self.log_button.setProperty("state", "idle")
        self.log_button.setToolTip("打开 FFmpeg Log")
        self.log_button.clicked.connect(self.open_log_dialog)
        layout.addWidget(self.log_button)
        self.settings_button = QToolButton()
        self.settings_button.setObjectName("settingsButton")
        self.settings_button.setText("⚙")
        self.settings_button.setAccessibleName("设置")
        self.settings_button.setToolTip("打开设置")
        self.settings_button.clicked.connect(self.open_settings_dialog)
        layout.addWidget(self.settings_button)
        return masthead

    def _set_settings_button_health(self, health: RuntimeHealth) -> None:
        if health.ok:
            self.settings_button.setProperty("state", "ok")
            self.settings_button.setToolTip("设置 · ffmpeg/ffprobe 可用")
        else:
            self.settings_button.setProperty("state", "error")
            self.settings_button.setToolTip("设置 · ffmpeg/ffprobe 不可用")
        self.settings_button.style().unpolish(self.settings_button)
        self.settings_button.style().polish(self.settings_button)

    def _mark_log_cleared(self) -> None:
        self._log_has_content = False
        self._log_has_error = False
        self._refresh_log_button()

    def _refresh_log_button(self) -> None:
        if self._log_has_error:
            self.log_button.setProperty("state", "error")
            self.log_button.setToolTip("打开 FFmpeg Log · 有错误")
        elif self._log_has_content:
            self.log_button.setProperty("state", "has")
            self.log_button.setToolTip("打开 FFmpeg Log")
        else:
            self.log_button.setProperty("state", "idle")
            self.log_button.setToolTip("打开 FFmpeg Log")
        self.log_button.style().unpolish(self.log_button)
        self.log_button.style().polish(self.log_button)
