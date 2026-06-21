from __future__ import annotations

from collections.abc import Set as AbstractSet
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

from desktop.app.ui.widgets.operation_parameter_form import OperationParameterForm
from desktop.app.ui.widgets.operation_selector import OperationSelector
from shared.contracts import MediaInfo, Operation


class OperationFormWidget(QWidget):
    file_browse_requested = Signal(str, str)
    spec_changed = Signal()
    stack_mode_toggled = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(236)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.operation_selector = OperationSelector()
        self.parameter_form = OperationParameterForm()
        self.operation_selector.operation_changed.connect(self._on_operation_changed)
        self.operation_selector.stack_mode_toggled.connect(self.stack_mode_toggled.emit)
        self.parameter_form.file_browse_requested.connect(self.file_browse_requested.emit)
        self.parameter_form.spec_changed.connect(self.spec_changed.emit)

        layout.addWidget(self.operation_selector, 3)
        layout.addWidget(self.parameter_form, 2)

    def selected_operation(self) -> Operation:
        return self.operation_selector.selected_operation()

    def select_operation(self, operation: Operation) -> None:
        self.operation_selector.select_operation(operation)

    def set_stack_mode(self, enabled: bool) -> None:
        self.operation_selector.set_stack_mode(enabled)

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

    def collect(self) -> tuple[Operation, dict[str, object], dict[str, Path]]:
        return self.parameter_form.collect()

    def apply_media_defaults(self, media_info: MediaInfo) -> None:
        self.parameter_form.apply_media_defaults(media_info)

    def _on_operation_changed(self, operation: object) -> None:
        if not isinstance(operation, Operation):
            return
        self.parameter_form.set_operation(operation, emit=False)
        self.spec_changed.emit()
