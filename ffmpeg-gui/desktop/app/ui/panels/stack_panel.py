from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
)

from desktop.app.ui.components import PanelActionBar, PanelFrame


class StackPanel(PanelFrame):
    add_requested = Signal()
    move_up_requested = Signal(int)
    move_down_requested = Signal(int)
    remove_requested = Signal(int)
    clear_requested = Signal()

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

        self.stack_list = QListWidget()
        self.stack_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.stack_list.setMinimumHeight(28)
        self.stack_list.setMaximumHeight(32)

        button_row = PanelActionBar()
        self.add_button = button_row.add_button("添加当前操作到 Stack", role="result")
        self.move_up_button = button_row.add_button("上移", role="quiet")
        self.move_down_button = button_row.add_button("下移", role="quiet")
        self.remove_button = button_row.add_button("移除", role="quiet")
        self.clear_button = button_row.add_button("清空", role="danger")
        self.add_button.clicked.connect(lambda _checked=False: self.add_requested.emit())
        self.move_up_button.clicked.connect(self._emit_move_up)
        self.move_down_button.clicked.connect(self._emit_move_down)
        self.remove_button.clicked.connect(self._emit_remove)
        self.clear_button.clicked.connect(lambda _checked=False: self.clear_requested.emit())

        layout.addWidget(self.stack_list)
        layout.addWidget(button_row)

        self.setVisible(False)
        self.set_busy(False)
        self.set_add_enabled(False)
        self.set_actions_enabled(False)

    def set_stack_mode(self, enabled: bool) -> None:
        self.setVisible(enabled)

    def set_items(self, items: list[str]) -> None:
        self._items = list(items)
        self.stack_list.clear()
        for item in items:
            QListWidgetItem(item, self.stack_list)
        self.list_label.setText(f"{len(items)} 项")
        self.set_actions_enabled(len(items) > 0)

    def has_items(self) -> bool:
        return bool(self._items)

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.stack_list.setEnabled(not busy)
        self.set_actions_enabled(self.has_items())

    def set_add_enabled(self, enabled: bool) -> None:
        self.add_button.setEnabled(enabled and not self._busy)

    def set_actions_enabled(self, has_items: bool) -> None:
        enabled = has_items and not self._busy
        self.move_up_button.setEnabled(enabled)
        self.move_down_button.setEnabled(enabled)
        self.remove_button.setEnabled(enabled)
        self.clear_button.setEnabled(enabled)

    def set_supported_note(self, supported: bool) -> None:
        if supported:
            self.mode_label.setText("当前操作支持加入 Stack。")
            return
        self.mode_label.setText("当前操作不支持加入 Stack。")

    def _emit_move_up(self) -> None:
        index = self._selected_index()
        if index is not None and index > 0:
            self.move_up_requested.emit(index)

    def _emit_move_down(self) -> None:
        index = self._selected_index()
        if index is not None and index < self.stack_list.count() - 1:
            self.move_down_requested.emit(index)

    def _emit_remove(self) -> None:
        index = self._selected_index()
        if index is not None:
            self.remove_requested.emit(index)

    def _selected_index(self) -> int | None:
        item = self.stack_list.currentItem()
        if item is None:
            return None
        return self.stack_list.row(item)
