from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
)

from desktop.app.ui.components import PanelActionBar, PanelFrame


class StackPanel(PanelFrame):
    add_requested = Signal()
    remove_requested = Signal(int)
    clear_requested = Signal()
    item_selected = Signal(int)
    item_moved = Signal(int, int)

    def __init__(self) -> None:
        super().__init__("Stack 队列", density="compact")
        self._items: list[str] = []
        self._busy = False
        self.setObjectName("stackPanel")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(148)
        self.setMaximumHeight(168)

        layout = self.body_layout()

        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        self.mode_label = QLabel("仅支持可链式单输入滤镜，顺序即执行顺序。")
        self.mode_label.setObjectName("mutedLabel")
        self.list_label = QLabel("0 项")
        self.list_label.setObjectName("mutedLabel")
        status_row.addWidget(self.mode_label, 1)
        status_row.addWidget(self.list_label)
        layout.addLayout(status_row)

        self.stack_chain = _StackChainView()
        self.stack_chain.item_selected.connect(self.item_selected.emit)
        self.stack_chain.item_moved.connect(self.item_moved.emit)

        button_row = PanelActionBar()
        self.add_button = button_row.add_button("添加当前操作到 Stack", role="result")
        self.remove_button = button_row.add_button("移除", role="quiet")
        self.clear_button = button_row.add_button("清空", role="danger")
        self.add_button.clicked.connect(lambda _checked=False: self.add_requested.emit())
        self.remove_button.clicked.connect(self._emit_remove)
        self.clear_button.clicked.connect(lambda _checked=False: self.clear_requested.emit())

        layout.addWidget(self.stack_chain)
        layout.addWidget(button_row)

        self.setVisible(False)
        self.set_busy(False)
        self.set_add_enabled(False)
        self.set_actions_enabled(False)

    def set_stack_mode(self, enabled: bool) -> None:
        self.setVisible(enabled)

    def set_items(self, items: list[str]) -> None:
        self._items = list(items)
        self.stack_chain.set_items(items)
        self.list_label.setText(f"{len(items)} 项")
        self.set_actions_enabled(len(items) > 0)

    def has_items(self) -> bool:
        return bool(self._items)

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.stack_chain.set_busy(busy)
        self.set_actions_enabled(self.has_items())

    def set_add_enabled(self, enabled: bool) -> None:
        self.add_button.setEnabled(enabled and not self._busy)

    def set_actions_enabled(self, has_items: bool) -> None:
        enabled = has_items and not self._busy
        self.remove_button.setEnabled(enabled)
        self.clear_button.setEnabled(enabled)

    def set_supported_note(self, supported: bool) -> None:
        if supported:
            self.mode_label.setText("当前操作支持加入 Stack；拖动标签调整顺序。")
            return
        self.mode_label.setText("当前操作不支持加入 Stack。")

    def _emit_remove(self) -> None:
        index = self._selected_index()
        if index is not None:
            self.remove_requested.emit(index)

    def _selected_index(self) -> int | None:
        return self.stack_chain.selected_index()


class _StackChainView(QFrame):
    item_selected = Signal(int)
    item_moved = Signal(int, int)

    def __init__(self) -> None:
        super().__init__()
        self._items: list[str] = []
        self._selected_index: int | None = None
        self._chip_buttons: list[_StackChipButton] = []
        self._drop_target_index: int | None = None
        self.setObjectName("stackChainView")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(44)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(8, 5, 8, 5)
        self._layout.setSpacing(6)
        self.set_items([])

    def set_items(self, items: list[str]) -> None:
        previous_index = self._selected_index
        previous_count = len(self._items)
        self._items = list(items)
        self._clear()

        if not self._items:
            empty_label = QLabel("还没有添加 Stack 步骤")
            empty_label.setObjectName("stackChainEmpty")
            self._layout.addWidget(empty_label)
            self._layout.addStretch(1)
            self._selected_index = None
            return

        for index, item in enumerate(self._items):
            chip = _StackChipButton(index, _chip_text(index, item))
            chip.setCheckable(True)
            chip.setProperty("role", "stackChip")
            chip.setCursor(Qt.CursorShape.OpenHandCursor)
            chip.setToolTip(f"第 {index + 1} 步：{item}\n点击查看参数；拖动调整执行顺序。")
            chip.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
            chip.setMinimumHeight(28)
            chip.setMaximumWidth(260)
            chip.setMinimumWidth(min(chip.sizeHint().width(), 260))
            chip.clicked.connect(lambda _checked=False, chip_index=index: self.select_index(chip_index, emit=True))
            chip.drag_moved.connect(self._on_chip_drag_moved)
            chip.drag_finished.connect(self._on_chip_drag_finished)
            self._chip_buttons.append(chip)
            self._layout.addWidget(chip)
            if index < len(self._items) - 1:
                arrow = QLabel("→")
                arrow.setObjectName("stackArrow")
                arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._layout.addWidget(arrow)

        self._layout.addStretch(1)
        if previous_index is None or len(self._items) > previous_count:
            selected_index = len(self._items) - 1
        else:
            selected_index = min(previous_index, len(self._items) - 1)
        self.select_index(selected_index)

    def selected_index(self) -> int | None:
        return self._selected_index

    def select_index(self, index: int, *, emit: bool = False) -> None:
        if index < 0 or index >= len(self._chip_buttons):
            return
        self._selected_index = index
        for chip_index, chip in enumerate(self._chip_buttons):
            chip.setChecked(chip_index == index)
        if emit:
            self.item_selected.emit(index)

    def move_item(self, from_index: int, to_index: int) -> None:
        if from_index < 0 or from_index >= len(self._chip_buttons):
            return
        if to_index < 0 or to_index >= len(self._chip_buttons):
            return
        if from_index == to_index:
            self.select_index(to_index)
            return
        self.select_index(to_index)
        self.item_moved.emit(from_index, to_index)

    def set_busy(self, busy: bool) -> None:
        self.setEnabled(not busy)
        for chip in self._chip_buttons:
            chip.setEnabled(not busy)

    def _on_chip_drag_moved(self, _from_index: int, position: QPoint) -> None:
        self._set_drop_target(self._target_index_from_position(position))

    def _on_chip_drag_finished(self, from_index: int, position: QPoint) -> None:
        to_index = self._target_index_from_position(position)
        self._set_drop_target(None)
        self.move_item(from_index, to_index)

    def _target_index_from_position(self, position: QPoint) -> int:
        if not self._chip_buttons:
            return 0
        for index, chip in enumerate(self._chip_buttons):
            if position.x() < chip.geometry().center().x():
                return index
        return len(self._chip_buttons) - 1

    def _set_drop_target(self, index: int | None) -> None:
        if index == self._drop_target_index:
            return
        self._drop_target_index = index
        for chip_index, chip in enumerate(self._chip_buttons):
            _set_dynamic_property(chip, "dropTarget", chip_index == index)

    def _clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        self._chip_buttons.clear()
        self._drop_target_index = None


class _StackChipButton(QPushButton):
    drag_moved = Signal(int, QPoint)
    drag_finished = Signal(int, QPoint)

    def __init__(self, index: int, text: str) -> None:
        super().__init__(text)
        self._index = index
        self._press_position: QPoint | None = None
        self._dragging = False

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_position = event.position().toPoint()
            self._dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._press_position is None or not event.buttons() & Qt.MouseButton.LeftButton:
            super().mouseMoveEvent(event)
            return
        distance = (event.position().toPoint() - self._press_position).manhattanLength()
        if not self._dragging and distance >= QApplication.startDragDistance():
            self._dragging = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            _set_dynamic_property(self, "dragging", True)
        if self._dragging:
            self.drag_moved.emit(self._index, self.mapToParent(event.position().toPoint()))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            self.drag_finished.emit(self._index, self.mapToParent(event.position().toPoint()))
            self._reset_drag_state()
            self.setDown(False)
            event.accept()
            return
        super().mouseReleaseEvent(event)
        self._reset_drag_state()

    def _reset_drag_state(self) -> None:
        self._press_position = None
        self._dragging = False
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        _set_dynamic_property(self, "dragging", False)


def _chip_text(index: int, item: str) -> str:
    text = item.strip()
    if len(text) > 28:
        text = f"{text[:25]}..."
    return f"{index + 1}. {text}"


def _set_dynamic_property(widget: QPushButton, name: str, value: bool) -> None:
    widget.setProperty(name, value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()
