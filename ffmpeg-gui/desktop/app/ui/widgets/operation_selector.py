from __future__ import annotations

from collections.abc import Set as AbstractSet

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QGridLayout, QPushButton, QSizePolicy, QWidget

from desktop.app.ui.components import FixedScrollArea, PanelFrame, SegmentOption, SegmentedToggle
from shared.contracts import OPERATION_LABELS, STACK_FILTER_OPERATIONS, Operation


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


class OperationSelector(PanelFrame):
    operation_changed = Signal(object)
    stack_mode_toggled = Signal(bool)

    def __init__(self) -> None:
        super().__init__("处理动作", description="先选择一个处理动作，参数会在下方更新。")
        self.setObjectName("operationFrame")
        self.setMinimumHeight(236)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._operation_buttons: dict[Operation, QPushButton] = {}
        self._selected_operation = Operation.convert
        self._form_enabled = True
        self._batch_mode = False
        self._batch_supported_operations: set[Operation] = set()
        self._stack_mode = False

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
        operation_grid = QGridLayout()
        operation_grid.setHorizontalSpacing(6)
        operation_grid.setVerticalSpacing(6)
        operation_columns = 8
        for index, operation in enumerate(OPERATION_LABELS):
            button = QPushButton(operation_card_text(operation))
            button.setCheckable(True)
            button.setProperty("role", "operationCard")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip(OPERATION_LABELS[operation])
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.setMinimumHeight(30)
            button.clicked.connect(lambda _checked=False, op=operation: self.select_operation(op))
            self.operation_button_group.addButton(button)
            self._operation_buttons[operation] = button
            operation_grid.addWidget(button, index // operation_columns, index % operation_columns)

        self.operation_grid_widget = QWidget()
        self.operation_grid_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.operation_grid_widget.setLayout(operation_grid)

        self.operation_scroll_area = FixedScrollArea(height=140)
        self.operation_scroll_area.setObjectName("operationScroll")
        self.operation_scroll_area.set_content_widget(self.operation_grid_widget)
        self.body_layout().addWidget(self.operation_scroll_area)
        self.body_layout().addStretch(1)
        self.select_operation(self._selected_operation, emit=False)

    def selected_operation(self) -> Operation:
        return self._selected_operation

    def operation_buttons(self) -> dict[Operation, QPushButton]:
        return dict(self._operation_buttons)

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
            self.set_description("Stack + 批量仅启用可重复执行的链式滤镜动作。")
            return
        if self._stack_mode:
            self.set_description("Stack 仅启用可链式的单输入滤镜动作。")
            return
        if self._batch_mode:
            self.set_description("多个文件仅启用可重复执行的动作。")
            return
        self.set_description("先选择一个处理动作，参数会在下方更新。")

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
            blockers.append("Stack 仅支持可链式单输入滤镜。")
        if self._batch_mode and operation not in self._batch_supported_operations:
            blockers.append("多个文件暂不支持此动作。")
        return blockers


_OPERATION_SHORT_LABELS: dict[Operation, str] = {
    Operation.convert: "转换格式",
    Operation.resize_compress: "缩放压缩",
    Operation.compress: "压缩视频",
    Operation.extract_audio: "抽取音频",
    Operation.gif: "生成 GIF",
    Operation.mute: "静音",
    Operation.rotate: "旋转翻转",
    Operation.crop: "裁剪",
    Operation.thumbnail: "提取封面",
    Operation.reverse: "倒放",
    Operation.fade: "淡入淡出",
    Operation.adjust: "画面调整",
    Operation.loop: "循环",
    Operation.strip_metadata: "移除元数据",
    Operation.pad: "画布补边",
    Operation.denoise: "去噪",
    Operation.boomerang: "倒放回放",
    Operation.sharpen_blur: "锐化模糊",
    Operation.speed: "速度调整",
    Operation.volume: "音量调整",
    Operation.normalize_audio: "响度标准化",
    Operation.subtitles: "嵌入字幕",
    Operation.media_info: "媒体探测",
    Operation.raw: "Raw 参数",
    Operation.overlay: "叠加",
    Operation.mix_audio: "混音",
    Operation.concat: "视频拼接",
    Operation.side_by_side: "并排对比",
    Operation.picture_in_picture: "画中画",
}


def operation_title_and_category(operation: Operation) -> tuple[str, str]:
    label = OPERATION_LABELS[operation]
    category, _, parsed_title = label.partition(" - ")
    title = _OPERATION_SHORT_LABELS.get(operation, parsed_title or label)
    return title, category or "通用"


def operation_card_text(operation: Operation) -> str:
    title, _category = operation_title_and_category(operation)
    return title
