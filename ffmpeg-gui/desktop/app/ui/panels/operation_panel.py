from __future__ import annotations

from collections.abc import Set as AbstractSet
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from desktop.app.ui.panels.command_preview_panel import CommandPreviewPanel
from desktop.app.ui.panels.stack_panel import StackPanel
from desktop.app.ui.widgets.operation_form import OperationFormWidget
from shared.contracts import MediaInfo, Operation, STACK_FILTER_OPERATIONS


class OperationPanel(QWidget):
    file_browse_requested = Signal(str, str)
    stack_mode_toggled = Signal(bool)
    stack_add_requested = Signal()
    stack_remove_requested = Signal(int)
    stack_clear_requested = Signal()
    stack_item_selected = Signal(int)
    stack_item_moved = Signal(int, int)
    command_preview_requested = Signal()
    minimum_height_changed = Signal()

    def __init__(self, command_preview_panel: CommandPreviewPanel | None = None) -> None:
        super().__init__()
        self.setObjectName("operationPanel")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self._busy = False
        self._stack_mode_enabled = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self._layout = layout

        self.command_preview_panel = command_preview_panel or CommandPreviewPanel()
        self.operation_form = OperationFormWidget(command_preview_widget=self.command_preview_panel)
        self.operation_form.file_browse_requested.connect(self.file_browse_requested.emit)
        self.operation_form.spec_changed.connect(self.refresh_stack_controls)
        self.operation_form.spec_changed.connect(self.command_preview_requested.emit)
        self.operation_form.minimum_height_changed.connect(self._sync_minimum_height)
        self.operation_form.stack_mode_toggled.connect(self.stack_mode_toggled.emit)
        self.operation_form.operation_activated.connect(self._handle_operation_activated)
        layout.addWidget(self.operation_form)

        self.stack_panel = StackPanel()
        self.stack_panel.remove_requested.connect(self.stack_remove_requested.emit)
        self.stack_panel.clear_requested.connect(self.stack_clear_requested.emit)
        self.stack_panel.item_selected.connect(self.stack_item_selected.emit)
        self.stack_panel.item_moved.connect(self.stack_item_moved.emit)
        self.stack_panel.output_options_changed.connect(self.command_preview_requested.emit)
        self.stack_panel.setVisible(False)
        layout.addWidget(self.stack_panel)
        layout.addStretch(1)
        self._sync_minimum_height()

    def selected_operation_payload(self) -> tuple[Operation, dict[str, object], dict[str, Path]]:
        return self.operation_form.collect()

    def selected_operation(self) -> Operation:
        return self.operation_form.selected_operation()

    def set_enabled(self, enabled: bool) -> None:
        self.operation_form.set_enabled(enabled)

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.operation_form.set_enabled(not busy)
        self.operation_form.set_stack_mode_enabled(not busy)
        self.stack_panel.set_busy(busy)
        if not busy:
            self.refresh_stack_controls()

    def is_busy(self) -> bool:
        return self._busy

    def set_batch_input_mode(self, enabled: bool, supported_operations: AbstractSet[Operation]) -> None:
        self.operation_form.set_batch_operation_support(enabled, supported_operations)
        self.refresh_stack_controls()

    def set_stack_mode(self, enabled: bool) -> None:
        self._stack_mode_enabled = enabled
        self.operation_form.set_stack_mode(enabled)
        self.stack_panel.setVisible(enabled)
        self.stack_panel.set_stack_mode(enabled)
        self._sync_minimum_height()
        self.refresh_stack_controls()

    def stack_mode(self) -> bool:
        return self.operation_form.stack_mode()

    def set_stack_items(self, items: list[str]) -> None:
        self.stack_panel.set_items(items)
        self.refresh_stack_controls()

    def stack_output_options(self) -> dict[str, object]:
        return self.stack_panel.stack_output_options()

    def set_operation_payload(
        self,
        operation: Operation,
        options: dict[str, object],
        extra_inputs: dict[str, Path],
    ) -> None:
        self.operation_form.set_operation_payload(operation, options, extra_inputs)

    def refresh_stack_controls(self) -> None:
        supported = self._is_stack_operation_supported()
        if self.stack_mode():
            self.stack_panel.set_supported_note(supported)
        self.stack_panel.set_actions_enabled(self.stack_panel.has_items())

    def apply_media_defaults(self, media_info: MediaInfo) -> None:
        self.operation_form.apply_media_defaults(media_info)

    def set_file_path(self, field_name: str, path: str) -> None:
        self.operation_form.set_file_path(field_name, path)

    def set_subtitle_path(self, path: str) -> None:
        self.operation_form.set_subtitle_path(path)

    def set_trim_start_seconds(self, seconds: float) -> None:
        self.operation_form.set_trim_start_seconds(seconds)

    def set_trim_end_seconds(self, seconds: float) -> None:
        self.operation_form.set_trim_end_seconds(seconds)

    def clear_trim_range(self) -> None:
        self.operation_form.clear_trim_range()

    def set_thumbnail_timestamp_seconds(self, seconds: float) -> bool:
        return self.operation_form.set_thumbnail_timestamp_seconds(seconds)

    def trim_range(self) -> tuple[float | None, float | None]:
        return self.operation_form.trim_range()

    def _is_stack_operation_supported(self) -> bool:
        return self.selected_operation() in STACK_FILTER_OPERATIONS

    def _handle_operation_activated(self, operation: object) -> None:
        if self._busy or not self.stack_mode():
            return
        if not isinstance(operation, Operation):
            return
        if operation not in STACK_FILTER_OPERATIONS:
            return
        self.stack_add_requested.emit()

    def _sync_minimum_height(self) -> None:
        minimum_height = self.operation_form.minimumHeight()
        if self._stack_mode_enabled:
            minimum_height += self._layout.spacing() + self.stack_panel.minimumHeight()
        self.setMinimumHeight(minimum_height)
        self.updateGeometry()
        self.minimum_height_changed.emit()
