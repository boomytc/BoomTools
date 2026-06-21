from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPaintEvent, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
)

from desktop.app.ui.components import PanelFrame
from shared.contracts import STACK_MAX_ITEMS


STACK_HINT = f"双击动作加入 · 拖动排序 · 最多 {STACK_MAX_ITEMS} 步"
STACK_LIMITED_HINT = f"仅可双击可链式动作 · 最多 {STACK_MAX_ITEMS} 步"
STACK_CHIP_MAX_WIDTH = 136
STACK_CHIP_TEXT_LIMIT = 12


class StackPanel(PanelFrame):
    remove_requested = Signal(int)
    clear_requested = Signal()
    item_selected = Signal(int)
    item_moved = Signal(int, int)

    def __init__(self) -> None:
        super().__init__("Stack 队列", description=STACK_HINT, density="compact")
        self._items: list[str] = []
        self._busy = False
        self.setObjectName("stackPanel")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(86)
        self.setMaximumHeight(112)

        self.count_label = QLabel(f"0/{STACK_MAX_ITEMS}")
        self.count_label.setObjectName("stackCountLabel")
        self.count_label.setToolTip(f"Stack 最多支持 {STACK_MAX_ITEMS} 个动作")
        self.add_action(self.count_label)

        self.clear_button = QPushButton("清空")
        self.clear_button.setProperty("role", "danger")
        self.clear_button.setProperty("density", "compact")
        self.clear_button.clicked.connect(lambda _checked=False: self.clear_requested.emit())
        self.add_action(self.clear_button)

        layout = self.body_layout()

        self.stack_chain = _StackChainView()
        self.stack_chain.item_selected.connect(self.item_selected.emit)
        self.stack_chain.item_moved.connect(self.item_moved.emit)
        self.stack_chain.item_removed.connect(self.remove_requested.emit)

        layout.addWidget(self.stack_chain)

        self.setVisible(False)
        self.set_busy(False)
        self.set_actions_enabled(False)

    def set_stack_mode(self, enabled: bool) -> None:
        self.setVisible(enabled)

    def set_items(self, items: list[str]) -> None:
        self._items = list(items)
        self.stack_chain.set_items(items)
        self.count_label.setText(f"{len(items)}/{STACK_MAX_ITEMS}")
        self.set_actions_enabled(len(items) > 0)

    def has_items(self) -> bool:
        return bool(self._items)

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.stack_chain.set_busy(busy)
        self.set_actions_enabled(self.has_items())

    def set_actions_enabled(self, has_items: bool) -> None:
        enabled = has_items and not self._busy
        self.clear_button.setEnabled(enabled)

    def set_supported_note(self, supported: bool) -> None:
        if supported:
            self.set_description(STACK_HINT)
            return
        self.set_description(STACK_LIMITED_HINT)


class _StackChainView(QFrame):
    item_selected = Signal(int)
    item_moved = Signal(int, int)
    item_removed = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self._items: list[str] = []
        self._selected_index: int | None = None
        self._chip_buttons: list[_StackChipButton] = []
        self._drop_target_index: int | None = None
        self._drop_slot: int | None = None
        self._drag_hot_spot = QPoint()
        self.setObjectName("stackChainView")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(36)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 2, 0, 2)
        self._layout.setSpacing(6)
        self._drop_marker = QFrame(self)
        self._drop_marker.setObjectName("stackDropMarker")
        self._drop_marker.setFixedSize(18, 28)
        self._drop_marker.hide()
        self._drag_ghost = QLabel(self)
        self._drag_ghost.setObjectName("stackDragGhost")
        self._drag_ghost.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        ghost_opacity = QGraphicsOpacityEffect(self._drag_ghost)
        ghost_opacity.setOpacity(0.72)
        self._drag_ghost.setGraphicsEffect(ghost_opacity)
        self._drag_ghost.hide()
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
            chip.setToolTip(f"第 {index + 1} 步：{item}\n点击查看参数；拖动调整执行顺序；点击右侧 x 移除。")
            chip.setAccessibleName(f"Stack 第 {index + 1} 步")
            chip.setAccessibleDescription("点击查看参数，拖动调整执行顺序，点击右侧 x 移除。")
            chip.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
            chip.setMinimumHeight(28)
            chip.setMaximumWidth(STACK_CHIP_MAX_WIDTH)
            chip.setMinimumWidth(min(chip.sizeHint().width(), STACK_CHIP_MAX_WIDTH))
            chip.clicked.connect(lambda _checked=False, chip_index=index: self.select_index(chip_index, emit=True))
            chip.remove_requested.connect(self.item_removed.emit)
            chip.drag_started.connect(self._on_chip_drag_started)
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

    def _on_chip_drag_started(self, from_index: int, position: QPoint, hot_spot: QPoint) -> None:
        self._show_drag_ghost(from_index, position, hot_spot)
        self._set_drop_slot(self._drop_slot_from_position(position))

    def _on_chip_drag_moved(self, from_index: int, position: QPoint) -> None:
        self._move_drag_ghost(position)
        slot = self._drop_slot_from_position(position)
        self._set_drop_slot(slot)
        self._set_drop_target(self._target_index_from_slot(from_index, slot))

    def _on_chip_drag_finished(self, from_index: int, position: QPoint) -> None:
        to_index = self._target_index_from_slot(from_index, self._drop_slot_from_position(position))
        self._clear_drag_feedback()
        self.move_item(from_index, to_index)

    def _drop_slot_from_position(self, position: QPoint) -> int:
        if not self._chip_buttons:
            return 0
        for index, chip in enumerate(self._chip_buttons):
            if position.x() < chip.geometry().center().x():
                return index
        return len(self._chip_buttons)

    def _target_index_from_slot(self, from_index: int, slot: int) -> int:
        if not self._chip_buttons:
            return 0
        target_slot = slot
        if target_slot > from_index:
            target_slot -= 1
        return max(0, min(target_slot, len(self._chip_buttons) - 1))

    def _set_drop_slot(self, slot: int | None) -> None:
        if slot == self._drop_slot:
            return
        self._drop_slot = slot
        if slot is None:
            self._hide_drop_marker()
            return
        self._show_drop_marker(slot)

    def _show_drop_marker(self, slot: int) -> None:
        self._remove_drop_marker_from_layout()
        insert_at = self._layout_index_for_slot(slot)
        self._layout.insertWidget(insert_at, self._drop_marker)
        self._drop_marker.show()
        self._layout.activate()

    def _hide_drop_marker(self) -> None:
        self._remove_drop_marker_from_layout()
        self._drop_marker.hide()
        self._drop_slot = None

    def _remove_drop_marker_from_layout(self) -> None:
        for index in range(self._layout.count()):
            item = self._layout.itemAt(index)
            if item is not None and item.widget() is self._drop_marker:
                self._layout.takeAt(index)
                break
        self._drop_marker.setParent(self)

    def _layout_index_for_slot(self, slot: int) -> int:
        if slot < len(self._chip_buttons):
            return self._layout_index_of_widget(self._chip_buttons[slot])
        return max(self._layout.count() - 1, 0)

    def _layout_index_of_widget(self, widget: QPushButton) -> int:
        for index in range(self._layout.count()):
            item = self._layout.itemAt(index)
            if item is not None and item.widget() is widget:
                return index
        return self._layout.count()

    def _set_drop_target(self, index: int | None) -> None:
        if index == self._drop_target_index:
            return
        self._drop_target_index = index
        for chip_index, chip in enumerate(self._chip_buttons):
            _set_dynamic_property(chip, "dropTarget", chip_index == index)

    def _show_drag_ghost(self, from_index: int, position: QPoint, hot_spot: QPoint) -> None:
        if from_index < 0 or from_index >= len(self._chip_buttons):
            return
        chip = self._chip_buttons[from_index]
        self._drag_ghost.setPixmap(chip.grab())
        self._drag_ghost.setFixedSize(chip.size())
        self._drag_hot_spot = hot_spot
        self._drag_ghost.move(position - hot_spot)
        self._drag_ghost.show()
        self._drag_ghost.raise_()

    def _move_drag_ghost(self, position: QPoint) -> None:
        if not self._drag_ghost.isVisible():
            return
        self._drag_ghost.move(position - self._drag_hot_spot)
        self._drag_ghost.raise_()

    def _clear_drag_feedback(self) -> None:
        self._hide_drop_marker()
        self._hide_drag_ghost()
        self._set_drop_target(None)

    def _hide_drag_ghost(self) -> None:
        self._drag_ghost.hide()
        self._drag_ghost.clear()
        self._drag_hot_spot = QPoint()

    def _clear(self) -> None:
        self._clear_drag_feedback()
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        self._chip_buttons.clear()
        self._drop_target_index = None
        self._drop_slot = None
        self._drop_marker.setParent(self)
        self._drag_ghost.setParent(self)


class _StackChipButton(QPushButton):
    drag_started = Signal(int, QPoint, QPoint)
    drag_moved = Signal(int, QPoint)
    drag_finished = Signal(int, QPoint)
    remove_requested = Signal(int)

    def __init__(self, index: int, text: str) -> None:
        super().__init__(text)
        self._index = index
        self._press_position: QPoint | None = None
        self._dragging = False
        self._close_pressed = False
        self._close_hovered = False
        self.setMouseTracking(True)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self._close_rect().contains(event.position().toPoint()):
                self._close_pressed = True
                self._press_position = None
                self._dragging = False
                _set_dynamic_property(self, "closeHover", True)
                event.accept()
                return
            self._press_position = event.position().toPoint()
            self._dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._close_pressed:
            self._set_close_hovered(self._close_rect().contains(event.position().toPoint()))
            event.accept()
            return
        self._set_close_hovered(self._close_rect().contains(event.position().toPoint()))
        if self._press_position is None or not event.buttons() & Qt.MouseButton.LeftButton:
            super().mouseMoveEvent(event)
            return
        distance = (event.position().toPoint() - self._press_position).manhattanLength()
        if not self._dragging and distance >= QApplication.startDragDistance():
            self._dragging = True
            self.drag_started.emit(self._index, self.mapToParent(event.position().toPoint()), self._press_position)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            _set_dynamic_property(self, "dragging", True)
        if self._dragging:
            self.drag_moved.emit(self._index, self.mapToParent(event.position().toPoint()))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._close_pressed:
            should_remove = self._close_rect().contains(event.position().toPoint())
            self._close_pressed = False
            self._set_close_hovered(should_remove)
            self.setDown(False)
            if should_remove:
                self.remove_requested.emit(self._index)
            event.accept()
            return
        if self._dragging:
            self.drag_finished.emit(self._index, self.mapToParent(event.position().toPoint()))
            self._reset_drag_state()
            self.setDown(False)
            event.accept()
            return
        super().mouseReleaseEvent(event)
        self._reset_drag_state()

    def leaveEvent(self, event: QEvent) -> None:
        self._set_close_hovered(False)
        super().leaveEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        close_rect = self._close_rect()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._close_hovered or self._close_pressed:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#31415e"))
            painter.drawRoundedRect(close_rect, 8, 8)
        painter.setPen(QColor("#6f7a8e") if not self.isEnabled() else QColor("#aeb9ce"))
        painter.drawText(close_rect, Qt.AlignmentFlag.AlignCenter, "x")
        painter.end()

    def _close_rect(self) -> QRect:
        side = 18
        return QRect(self.width() - side - 6, (self.height() - side) // 2, side, side)

    def _set_close_hovered(self, hovered: bool) -> None:
        if hovered == self._close_hovered:
            return
        self._close_hovered = hovered
        _set_dynamic_property(self, "closeHover", hovered)
        if hovered:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        elif self._dragging:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            self.setCursor(Qt.CursorShape.OpenHandCursor)

    def _reset_drag_state(self) -> None:
        self._press_position = None
        self._dragging = False
        self._close_pressed = False
        if self._close_hovered:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        _set_dynamic_property(self, "dragging", False)


def _chip_text(index: int, item: str) -> str:
    text = _compact_chip_label(item)
    if len(text) > STACK_CHIP_TEXT_LIMIT:
        text = f"{text[: STACK_CHIP_TEXT_LIMIT - 3]}..."
    return f"{index + 1}. {text}"


def _compact_chip_label(item: str) -> str:
    text = item.strip()
    _category, separator, title = text.partition(" - ")
    if separator and title:
        text = title.strip()
    if len(text) > STACK_CHIP_TEXT_LIMIT and " (" in text:
        text = text.split(" (", 1)[0].strip()
    return text


def _set_dynamic_property(widget: QPushButton, name: str, value: bool) -> None:
    widget.setProperty(name, value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()
