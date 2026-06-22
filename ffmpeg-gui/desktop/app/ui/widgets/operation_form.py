from __future__ import annotations

from collections.abc import Set as AbstractSet
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QSizePolicy, QWidget

from desktop.app.ui.widgets.operation_parameter_form import OperationParameterForm
from desktop.app.ui.widgets.operation_selector import OperationSelector
from shared.contracts import MediaInfo, Operation


class OperationFormWidget(QWidget):
    file_browse_requested = Signal(str, str)
    spec_changed = Signal()
    stack_mode_toggled = Signal(bool)
    operation_activated = Signal(object)
    minimum_height_changed = Signal()

    def __init__(self, command_preview_widget: QWidget | None = None) -> None:
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(8)

        self.operation_selector = OperationSelector()
        self.parameter_form = OperationParameterForm()
        self.command_preview_widget = command_preview_widget
        self.operation_selector.operation_changed.connect(self._on_operation_changed)
        self.operation_selector.operation_activated.connect(self.operation_activated.emit)
        self.operation_selector.stack_mode_toggled.connect(self.stack_mode_toggled.emit)
        self.parameter_form.file_browse_requested.connect(self.file_browse_requested.emit)
        self.parameter_form.spec_changed.connect(self.spec_changed.emit)
        height_mode_changed = getattr(command_preview_widget, "height_mode_changed", None)
        if height_mode_changed is not None:
            height_mode_changed.connect(self._sync_minimum_height)

        layout.addWidget(self.operation_selector, 0, 0)
        if command_preview_widget is not None:
            layout.addWidget(command_preview_widget, 1, 0)
            layout.addWidget(self.parameter_form, 0, 1, 2, 1)
            layout.setRowMinimumHeight(0, self.operation_selector.minimumHeight())
            layout.setRowMinimumHeight(1, command_preview_widget.minimumHeight())
        else:
            layout.addWidget(self.parameter_form, 0, 1)
            layout.setRowMinimumHeight(0, self.operation_selector.minimumHeight())
        layout.setColumnStretch(0, 3)
        layout.setColumnStretch(1, 2)
        self._sync_minimum_height()

    def selected_operation(self) -> Operation:
        return self.operation_selector.selected_operation()

    def select_operation(self, operation: Operation) -> None:
        self.operation_selector.select_operation(operation)

    def set_operation_payload(
        self,
        operation: Operation,
        options: dict[str, object],
        extra_inputs: dict[str, Path],
    ) -> None:
        self.operation_selector.select_operation(operation, emit=False, force=True)
        self.parameter_form.set_operation(operation, emit=False)
        self.parameter_form.set_payload(options, extra_inputs)
        self.spec_changed.emit()

    def set_stack_mode(self, enabled: bool) -> None:
        self.operation_selector.set_stack_mode(enabled)
        self._sync_minimum_height()

    def stack_mode(self) -> bool:
        return self.operation_selector.stack_mode()

    def set_stack_mode_enabled(self, enabled: bool) -> None:
        self.operation_selector.set_stack_mode_enabled(enabled)

    def set_enabled(self, enabled: bool) -> None:
        self.operation_selector.set_enabled(enabled)
        self.parameter_form.set_enabled(enabled)

    def set_batch_operation_support(self, enabled: bool, supported_operations: AbstractSet[Operation]) -> None:
        self.operation_selector.set_batch_operation_support(enabled, supported_operations)

    def set_file_path(self, field_name: str, path: str) -> None:
        self.parameter_form.set_file_path(field_name, path)

    def set_subtitle_path(self, path: str) -> None:
        self.parameter_form.set_subtitle_path(path)

    def set_trim_start_seconds(self, seconds: float) -> None:
        self.parameter_form.set_trim_start_seconds(seconds)

    def set_trim_end_seconds(self, seconds: float) -> None:
        self.parameter_form.set_trim_end_seconds(seconds)

    def clear_trim_range(self) -> None:
        self.parameter_form.clear_trim_range()

    def set_thumbnail_timestamp_seconds(self, seconds: float) -> bool:
        return self.parameter_form.set_thumbnail_timestamp_seconds(seconds)

    def trim_range(self) -> tuple[float | None, float | None]:
        return self.parameter_form.trim_range()

    def collect(self) -> tuple[Operation, dict[str, object], dict[str, Path]]:
        return self.parameter_form.collect()

    def apply_media_defaults(self, media_info: MediaInfo) -> None:
        self.parameter_form.apply_media_defaults(media_info)

    def _on_operation_changed(self, operation: object) -> None:
        if not isinstance(operation, Operation):
            return
        self.parameter_form.set_operation(operation, emit=False)
        self.spec_changed.emit()

    def _sync_minimum_height(self) -> None:
        minimum_height = self.operation_selector.minimumHeight()
        if self.command_preview_widget is not None:
            minimum_height += self.layout().verticalSpacing() + self.command_preview_widget.minimumHeight()
        self.setMinimumHeight(minimum_height)
        self.updateGeometry()
        self.minimum_height_changed.emit()
