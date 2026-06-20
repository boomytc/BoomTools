from __future__ import annotations

from collections.abc import Set as AbstractSet
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QRadioButton, QVBoxLayout, QWidget

from desktop.app.ui.panels.stack_panel import StackPanel
from desktop.app.ui.widgets.operation_form import OperationFormWidget
from shared.contracts import MediaInfo, Operation, STACK_FILTER_OPERATIONS


class OperationPanel(QWidget):
    file_browse_requested = Signal(str, str)
    start_requested = Signal()
    cancel_requested = Signal()
    cancel_queue_requested = Signal()
    remove_pending_requested = Signal()
    stack_mode_toggled = Signal(bool)
    stack_add_requested = Signal()
    stack_move_up_requested = Signal(int)
    stack_move_down_requested = Signal(int)
    stack_remove_requested = Signal(int)
    stack_clear_requested = Signal()
    command_preview_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("operationPanel")
        self._busy = False
        self._pending_count = 0
        self._batch_running = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        control_row = QHBoxLayout()
        control_row.setSpacing(8)
        self.single_mode_radio = QRadioButton("单操作")
        self.stack_mode_radio = QRadioButton("Stack 链式")
        self.single_mode_radio.setChecked(True)
        control_row.addWidget(self.single_mode_radio)
        control_row.addWidget(self.stack_mode_radio)

        self.single_mode_radio.toggled.connect(lambda checked: self.stack_mode_toggled.emit(False) if checked else None)
        self.stack_mode_radio.toggled.connect(lambda checked: self.stack_mode_toggled.emit(True) if checked else None)
        control_row.addStretch(1)
        self.start_button = QPushButton("开始处理")
        self.start_button.setObjectName("primaryButton")
        self.cancel_button = QPushButton("取消当前")
        self.cancel_button.setProperty("role", "danger")
        self.cancel_queue_button = QPushButton("取消队列")
        self.cancel_queue_button.setProperty("role", "danger")
        self.remove_pending_button = QPushButton("移除未运行")
        self.remove_pending_button.setProperty("role", "quiet")
        self.cancel_button.setEnabled(False)
        self.cancel_queue_button.setEnabled(False)
        self.remove_pending_button.setEnabled(False)
        self.start_button.clicked.connect(lambda _checked=False: self.start_requested.emit())
        self.cancel_button.clicked.connect(lambda _checked=False: self.cancel_requested.emit())
        self.cancel_queue_button.clicked.connect(lambda _checked=False: self.cancel_queue_requested.emit())
        self.remove_pending_button.clicked.connect(lambda _checked=False: self.remove_pending_requested.emit())
        control_row.addWidget(self.start_button)
        control_row.addWidget(self.cancel_button)
        control_row.addWidget(self.cancel_queue_button)
        control_row.addWidget(self.remove_pending_button)
        layout.addLayout(control_row)

        self.operation_form = OperationFormWidget()
        self.operation_form.file_browse_requested.connect(self.file_browse_requested.emit)
        self.operation_form.spec_changed.connect(self.refresh_stack_controls)
        self.operation_form.spec_changed.connect(self.command_preview_requested.emit)
        layout.addWidget(self.operation_form, 1)

        self.stack_panel = StackPanel()
        self.stack_panel.add_requested.connect(self.stack_add_requested.emit)
        self.stack_panel.move_up_requested.connect(self.stack_move_up_requested.emit)
        self.stack_panel.move_down_requested.connect(self.stack_move_down_requested.emit)
        self.stack_panel.remove_requested.connect(self.stack_remove_requested.emit)
        self.stack_panel.clear_requested.connect(self.stack_clear_requested.emit)
        self.stack_panel.setVisible(False)
        layout.addWidget(self.stack_panel)

    def selected_operation_payload(self) -> tuple[Operation, dict[str, object], dict[str, Path]]:
        return self.operation_form.collect()

    def selected_operation(self) -> Operation:
        return self.operation_form.selected_operation()

    def set_enabled(self, enabled: bool) -> None:
        self.operation_form.set_enabled(enabled)

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.start_button.setEnabled(not busy)
        self.cancel_button.setEnabled(busy)
        self.operation_form.set_enabled(not busy)
        self.single_mode_radio.setEnabled(not busy)
        self.stack_mode_radio.setEnabled(not busy)
        self.stack_panel.set_busy(busy)
        self._sync_batch_buttons()
        if busy:
            self.stack_panel.set_add_enabled(False)
        else:
            self.refresh_stack_controls()

    def is_busy(self) -> bool:
        return self._busy

    def set_start_enabled(self, enabled: bool) -> None:
        self.start_button.setEnabled(enabled and not self._busy)

    def set_batch_buttons(self, pending_count: int, running: bool) -> None:
        self._pending_count = pending_count
        self._batch_running = running
        self._sync_batch_buttons()

    def set_batch_input_mode(self, enabled: bool, supported_operations: AbstractSet[Operation]) -> None:
        self.operation_form.set_batch_operation_support(enabled, supported_operations)
        self.refresh_stack_controls()

    def set_stack_mode(self, enabled: bool) -> None:
        self.stack_mode_radio.setChecked(enabled)
        self.single_mode_radio.setChecked(not enabled)
        self.stack_panel.setVisible(enabled)
        self.stack_panel.set_stack_mode(enabled)
        self.refresh_stack_controls()

    def stack_mode(self) -> bool:
        return self.stack_mode_radio.isChecked()

    def set_stack_items(self, items: list[str]) -> None:
        self.stack_panel.set_items(items)
        self.refresh_stack_controls()

    def refresh_stack_controls(self) -> None:
        supported = self._is_stack_operation_supported()
        self.stack_panel.set_add_enabled(self.stack_mode() and supported)
        if self.stack_mode():
            self.stack_panel.set_supported_note(supported)
        self.stack_panel.set_actions_enabled(self.stack_panel.has_items())

    def apply_media_defaults(self, media_info: MediaInfo) -> None:
        self.operation_form.apply_media_defaults(media_info)

    def set_file_path(self, field_name: str, path: str) -> None:
        self.operation_form.set_file_path(field_name, path)

    def set_subtitle_path(self, path: str) -> None:
        self.operation_form.set_subtitle_path(path)

    def _is_stack_operation_supported(self) -> bool:
        return self.selected_operation() in STACK_FILTER_OPERATIONS

    def _sync_batch_buttons(self) -> None:
        self.remove_pending_button.setEnabled(self._pending_count > 0 and not self._batch_running and not self._busy)
        self.cancel_queue_button.setEnabled(self._batch_running)
