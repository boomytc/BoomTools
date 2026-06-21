from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QCloseEvent, QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from desktop.app.core.constants import WINDOW_TITLE
from desktop.app.runtime.binaries import RuntimeHealth
from desktop.app.ui.dialogs import LogDialog, SettingsDialog
from desktop.app.ui.layouts import DashboardLayout
from desktop.app.ui.panels import CommandPreviewPanel, OperationPanel, RuntimePanel, TaskPanel
from desktop.app.ui.widgets.task_table_model import TaskTableModel
from shared.contracts import BATCH_SUPPORTED_OPERATIONS, MediaInfo, Operation


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
    task_remove_requested = Signal(str)
    open_output_requested = Signal()
    open_output_dir_requested = Signal()
    stack_mode_toggled = Signal(bool)
    stack_add_requested = Signal()
    stack_move_up_requested = Signal(int)
    stack_move_down_requested = Signal(int)
    stack_remove_requested = Signal(int)
    stack_clear_requested = Signal()
    stack_item_selected = Signal(int)
    command_preview_requested = Signal()
    copy_output_path_requested = Signal()
    closing = Signal()

    def __init__(self, task_model: TaskTableModel) -> None:
        super().__init__()
        self._last_output_path: Path | None = None
        self._log_has_content = False
        self._log_has_error = False
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(1320, 920)
        self.setMinimumSize(1080, 860)

        central = QWidget()
        central.setObjectName("appRoot")
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        self.runtime_panel = RuntimePanel()
        self.operation_panel = OperationPanel()
        self.command_preview_panel = CommandPreviewPanel()
        self.task_panel = TaskPanel(task_model)
        self.dashboard_layout = DashboardLayout(
            runtime_panel=self.runtime_panel,
            operation_panel=self.operation_panel,
            command_preview_panel=self.command_preview_panel,
            task_panel=self.task_panel,
        )
        self.settings_dialog = SettingsDialog(self)
        self.log_dialog = LogDialog(self)
        self._connect_panel_signals()

        root.addWidget(self._create_masthead())
        root.addWidget(self.dashboard_layout, 1)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Ready")

    def set_initial_paths(self, *, ffmpeg_bin: str, ffprobe_bin: str, output_dir: Path) -> None:
        self.settings_dialog.set_initial_paths(ffmpeg_bin=ffmpeg_bin, ffprobe_bin=ffprobe_bin)
        self.runtime_panel.set_output_dir_text(str(output_dir))

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
        return self.runtime_panel.selected_output_dir()

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
        self.task_panel.set_busy(busy)
        self.settings_dialog.set_busy(busy)

    def set_start_enabled(self, enabled: bool) -> None:
        busy = self.operation_panel.is_busy()
        effective_enabled = enabled and not busy
        self.task_panel.set_start_enabled(effective_enabled)

    def set_batch_progress(self, current: int, total: int) -> None:
        self.runtime_panel.set_batch_progress(current, total)

    def set_batch_buttons(self, pending_count: int, running: bool) -> None:
        self.task_panel.set_batch_buttons(pending_count=pending_count, running=running)

    def set_progress(self, progress: float | None) -> None:
        self.task_panel.refresh_total_progress()

    def reset_progress(self) -> None:
        self.task_panel.refresh_total_progress()

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

    def current_output_path(self) -> Path | None:
        return self._effective_output_path()

    def set_stack_mode(self, enabled: bool) -> None:
        self.operation_panel.set_stack_mode(enabled)

    def stack_mode(self) -> bool:
        return self.operation_panel.stack_mode()

    def set_stack_items(self, items: list[str]) -> None:
        self.operation_panel.set_stack_items(items)

    def set_operation_payload(
        self,
        operation: Operation,
        options: dict[str, object],
        extra_inputs: dict[str, Path],
    ) -> None:
        self.operation_panel.set_operation_payload(operation, options, extra_inputs)

    def set_batch_input_mode(self, enabled: bool) -> None:
        self.runtime_panel.set_batch_input_mode(enabled, emit=False)
        self.operation_panel.set_batch_input_mode(enabled, BATCH_SUPPORTED_OPERATIONS)
        self.command_preview_panel.set_batch_mode(enabled)

    def set_batch_input_paths(self, paths: list[str | Path]) -> None:
        self.runtime_panel.set_batch_paths(paths)

    def refresh_stack_controls(self) -> None:
        self.operation_panel.refresh_stack_controls()

    def _update_stack_add_enabled(self) -> None:
        self.refresh_stack_controls()

    def set_command_preview(self, command: str) -> None:
        self.command_preview_panel.set_command(command)

    def set_output_estimate(self, _estimate: str) -> None:
        pass

    def selected_operation_payload(self):
        return self.operation_panel.selected_operation_payload()

    def selected_operation(self) -> Operation:
        return self.operation_panel.selected_operation()

    def show_error(self, message: str) -> None:
        self.statusBar().showMessage(message)
        QMessageBox.warning(self, "错误", message)

    def show_status(self, message: str) -> None:
        self.statusBar().showMessage(message)

    def choose_input_file(self) -> None:
        self.choose_batch_files()

    def choose_batch_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "添加媒体文件", self.runtime_panel.input_path_text())
        if not paths:
            return
        self.runtime_panel.set_batch_paths(paths)
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
        output_path = self._effective_output_path()
        if output_path and output_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(output_path)))

    def open_output_dir(self) -> None:
        output_path = self._effective_output_path()
        if output_path:
            directory = output_path.parent
        else:
            directory = self.selected_output_dir()
        if directory and directory.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory)))

    def copy_output_path(self) -> None:
        output_path = self._effective_output_path()
        if not output_path:
            self.show_status("当前无可复制的输出路径")
            return
        QGuiApplication.clipboard().setText(str(output_path))
        self.show_status("已复制输出路径到剪贴板")

    def _effective_output_path(self) -> Path | None:
        return self.task_panel.selected_output_path() or self._last_output_path

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
        self.runtime_panel.output_dir_requested.connect(self.choose_output_dir)
        self.settings_dialog.check_requested.connect(self.refresh_requested.emit)

        self.operation_panel.file_browse_requested.connect(self.choose_operation_file)
        self.operation_panel.stack_mode_toggled.connect(self.stack_mode_toggled.emit)
        self.operation_panel.stack_add_requested.connect(self.stack_add_requested.emit)
        self.operation_panel.stack_move_up_requested.connect(self.stack_move_up_requested.emit)
        self.operation_panel.stack_move_down_requested.connect(self.stack_move_down_requested.emit)
        self.operation_panel.stack_remove_requested.connect(self.stack_remove_requested.emit)
        self.operation_panel.stack_clear_requested.connect(self.stack_clear_requested.emit)
        self.operation_panel.stack_item_selected.connect(self.stack_item_selected.emit)
        self.operation_panel.command_preview_requested.connect(self.command_preview_requested.emit)

        self.task_panel.open_output_requested.connect(self.open_output_requested.emit)
        self.task_panel.open_output_dir_requested.connect(self.open_output_dir_requested.emit)
        self.task_panel.copy_output_path_requested.connect(self.copy_output_path_requested.emit)
        self.task_panel.remove_task_requested.connect(self.task_remove_requested.emit)
        self.task_panel.start_requested.connect(self.start_requested.emit)
        self.task_panel.cancel_requested.connect(self.cancel_requested.emit)
        self.task_panel.cancel_queue_requested.connect(self.cancel_queue_requested.emit)
        self.task_panel.remove_pending_requested.connect(self.remove_pending_requested.emit)
        self.command_preview_panel.command_copied.connect(lambda: self.show_status("已复制命令预览到剪贴板"))
        self.log_dialog.cleared.connect(self._mark_log_cleared)

    def _on_input_mode_changed(self, batch_mode: bool) -> None:
        self.operation_panel.set_batch_input_mode(batch_mode, BATCH_SUPPORTED_OPERATIONS)
        self.command_preview_panel.set_batch_mode(batch_mode)
        self.input_mode_changed.emit(batch_mode)

    def _create_masthead(self) -> QFrame:
        masthead = QFrame()
        masthead.setObjectName("masthead")
        masthead.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
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
