from __future__ import annotations

from collections.abc import Set as AbstractSet

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QButtonGroup, QGridLayout, QPushButton, QSizePolicy, QWidget

from desktop.app.ui.components import FixedScrollArea, PanelFrame, SegmentOption, SegmentedToggle
from shared.contracts import OPERATION_LABELS, STACK_FILTER_OPERATIONS, Operation, operation_short_label


STACK_MODE_FALLBACK_ORDER = (
    Operation.rotate,
    Operation.crop,
    Operation.adjust,
    Operation.denoise,
    Operation.sharpen_blur,
    Operation.pad,
    Operation.speed,
    Operation.volume,
    Operation.fade,
    Operation.resize_compress,
)

MAX_OPERATION_COLUMNS = 8
MIN_OPERATION_CARD_WIDTH = 78
OPERATION_GRID_SPACING = 6


class OperationSelector(PanelFrame):
    operation_changed = Signal(object)
    operation_activated = Signal(object)
    stack_mode_toggled = Signal(bool)

    def __init__(self) -> None:
        super().__init__("动作", description="选择动作后配置参数。")
        self.setObjectName("operationFrame")
        self.setMinimumHeight(236)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._operation_buttons: dict[Operation, QPushButton] = {}
        self._selected_operation = Operation.convert
        self._form_enabled = True
        self._batch_mode = False
        self._batch_supported_operations: set[Operation] = set()
        self._stack_mode = False
        self._operation_order = list(OPERATION_LABELS)
        self._operation_columns = 0

        self.mode_toggle = SegmentedToggle(
            [
                SegmentOption("single", "单操作"),
                SegmentOption("stack", "Stack 链式"),
            ]
        )
        self.mode_toggle.value_changed.connect(self._on_mode_value_changed)
        self.add_action(self.mode_toggle)

        self.operation_button_group = QButtonGroup(self)
        self.operation_button_group.setExclusive(True)
        self.operation_grid = QGridLayout()
        self.operation_grid.setHorizontalSpacing(OPERATION_GRID_SPACING)
        self.operation_grid.setVerticalSpacing(OPERATION_GRID_SPACING)
        for operation in self._operation_order:
            button = _OperationButton(operation, operation_card_text(operation))
            button.setCheckable(True)
            button.setProperty("role", "operationCard")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip(OPERATION_LABELS[operation])
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.setMinimumHeight(30)
            button.clicked.connect(lambda _checked=False, op=operation: self.select_operation(op))
            button.activated.connect(self._activate_operation)
            self.operation_button_group.addButton(button)
            self._operation_buttons[operation] = button

        self.operation_grid_widget = QWidget()
        self.operation_grid_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.operation_grid_widget.setMinimumWidth(0)
        self.operation_grid_widget.setLayout(self.operation_grid)

        self.operation_scroll_area = FixedScrollArea(height=140)
        self.operation_scroll_area.setObjectName("operationScroll")
        self.operation_scroll_area.set_content_widget(self.operation_grid_widget)
        self.operation_scroll_area.viewport().installEventFilter(self)
        self.body_layout().addWidget(self.operation_scroll_area)
        self.body_layout().addStretch(1)
        self._relayout_operation_grid()
        self.select_operation(self._selected_operation, emit=False)

    def selected_operation(self) -> Operation:
        return self._selected_operation

    def operation_buttons(self) -> dict[Operation, QPushButton]:
        return dict(self._operation_buttons)

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if watched is self.operation_scroll_area.viewport() and event.type() == QEvent.Type.Resize:
            self._relayout_operation_grid()
        return super().eventFilter(watched, event)

    def set_stack_mode(self, enabled: bool) -> None:
        self.mode_toggle.set_value("stack" if enabled else "single", force=True)
        self._apply_stack_mode(enabled)

    def stack_mode(self) -> bool:
        return self._stack_mode

    def set_stack_mode_enabled(self, enabled: bool) -> None:
        self.mode_toggle.button("single").setEnabled(enabled)
        self.mode_toggle.button("stack").setEnabled(enabled)

    def set_enabled(self, enabled: bool) -> None:
        self._form_enabled = enabled
        self._sync_operation_button_states()

    def set_batch_operation_support(self, enabled: bool, supported_operations: AbstractSet[Operation]) -> None:
        self._batch_mode = enabled
        self._batch_supported_operations = set(supported_operations)
        self._sync_operation_hint()
        self._ensure_selected_operation_available()
        self._sync_operation_button_states()

    def select_operation(self, operation: Operation, *, emit: bool = True, force: bool = False) -> None:
        if not force and not self._operation_allowed_by_modes(operation):
            return
        if operation == self._selected_operation and any(button.isChecked() for button in self._operation_buttons.values()):
            return
        self._selected_operation = operation
        for candidate, button in self._operation_buttons.items():
            button.setChecked(candidate == operation)
        if emit:
            self.operation_changed.emit(operation)
        self._sync_operation_button_states()

    def _first_available_operation(self) -> Operation | None:
        if self._stack_mode:
            for operation in STACK_MODE_FALLBACK_ORDER:
                if self._operation_allowed_by_modes(operation):
                    return operation
        for operation in OPERATION_LABELS:
            if self._operation_allowed_by_modes(operation):
                return operation
        return None

    def _sync_operation_hint(self) -> None:
        if self._stack_mode and self._batch_mode:
            self.set_description("Stack + 批量仅启用可重复执行的链式动作。")
            return
        if self._stack_mode:
            self.set_description("Stack 仅启用可链式的单输入动作。")
            return
        if self._batch_mode:
            self.set_description("多个文件仅启用可重复执行的动作。")
            return
        self.set_description("选择动作后配置参数。")

    def _sync_operation_button_states(self) -> None:
        for operation, button in self._operation_buttons.items():
            available = self._operation_is_available(operation)
            button.setEnabled(available)
            button.setCursor(Qt.CursorShape.PointingHandCursor if available else Qt.CursorShape.ArrowCursor)
            button.setToolTip(self._operation_tooltip(operation))

    def _operation_is_available(self, operation: Operation) -> bool:
        if not self._form_enabled:
            return False
        return self._operation_allowed_by_modes(operation)

    def _operation_tooltip(self, operation: Operation) -> str:
        label = OPERATION_LABELS[operation]
        blockers = self._operation_mode_blockers(operation)
        if blockers:
            return f"{label}\n" + "\n".join(blockers)
        return label

    def _on_mode_value_changed(self, value: str) -> None:
        stack_enabled = value == "stack"
        self._apply_stack_mode(stack_enabled)
        self.stack_mode_toggled.emit(stack_enabled)

    def _activate_operation(self, operation: object) -> None:
        if not isinstance(operation, Operation):
            return
        self.select_operation(operation)
        if self._operation_is_available(operation) and self._selected_operation is operation:
            self.operation_activated.emit(operation)

    def _apply_stack_mode(self, enabled: bool) -> None:
        self._stack_mode = enabled
        self._sync_operation_hint()
        self._ensure_selected_operation_available()
        self._sync_operation_button_states()

    def _ensure_selected_operation_available(self) -> None:
        if self._operation_allowed_by_modes(self._selected_operation):
            return
        replacement = self._first_available_operation()
        if replacement is not None:
            self.select_operation(replacement)

    def _operation_allowed_by_modes(self, operation: Operation) -> bool:
        return not self._operation_mode_blockers(operation)

    def _operation_mode_blockers(self, operation: Operation) -> list[str]:
        blockers: list[str] = []
        if self._stack_mode and operation not in STACK_FILTER_OPERATIONS:
            blockers.append("Stack 仅支持可链式单输入动作。")
        if self._batch_mode and operation not in self._batch_supported_operations:
            blockers.append("多个文件暂不支持此动作。")
        return blockers

    def _relayout_operation_grid(self) -> None:
        columns = self._operation_columns_for_width(self._operation_grid_available_width())
        if columns == self._operation_columns:
            return
        self._operation_columns = columns
        for button in self._operation_buttons.values():
            self.operation_grid.removeWidget(button)
        for index, operation in enumerate(self._operation_order):
            self.operation_grid.addWidget(self._operation_buttons[operation], index // columns, index % columns)
        for column in range(MAX_OPERATION_COLUMNS):
            self.operation_grid.setColumnStretch(column, 1 if column < columns else 0)
        self.operation_grid_widget.updateGeometry()

    def _operation_grid_available_width(self) -> int:
        viewport_width = self.operation_scroll_area.viewport().width()
        if viewport_width > 0:
            return viewport_width
        content_margins = self.body_layout().contentsMargins()
        return max(0, self.width() - content_margins.left() - content_margins.right())

    def _operation_columns_for_width(self, available_width: int) -> int:
        if available_width <= 0:
            return MAX_OPERATION_COLUMNS
        button_width = max(
            MIN_OPERATION_CARD_WIDTH,
            max((button.sizeHint().width() for button in self._operation_buttons.values()), default=0),
        )
        columns = (available_width + OPERATION_GRID_SPACING) // (button_width + OPERATION_GRID_SPACING)
        return max(1, min(MAX_OPERATION_COLUMNS, columns))


class _OperationButton(QPushButton):
    activated = Signal(object)

    def __init__(self, operation: Operation, text: str) -> None:
        super().__init__(text)
        self._operation = operation

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self.activated.emit(self._operation)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


def operation_card_text(operation: Operation) -> str:
    return operation_short_label(operation)
