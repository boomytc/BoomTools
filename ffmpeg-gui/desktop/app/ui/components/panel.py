from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget


class PanelFrame(QFrame):
    def __init__(self, title: str, *, description: str = "", density: str = "compact") -> None:
        super().__init__()
        self.setObjectName("panelFrame")
        self.setProperty("role", "panel")
        self.setProperty("density", density)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        margins = (12, 10, 12, 10) if density == "compact" else (14, 12, 14, 12)
        spacing = 8 if density == "compact" else 10

        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(*margins)
        self._root_layout.setSpacing(spacing)

        self.header_widget = QWidget()
        self.header_widget.setObjectName("panelHeader")
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        title_block = QHBoxLayout()
        title_block.setContentsMargins(0, 0, 0, 0)
        title_block.setSpacing(8)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionTitle")
        title_block.addWidget(self.title_label, 0, Qt.AlignmentFlag.AlignVCenter)
        self.description_label = QLabel(description)
        self.description_label.setObjectName("panelHeaderHint")
        self.description_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.description_label.setMinimumWidth(0)
        self.description_label.setToolTip(description)
        self.description_label.setVisible(bool(description))
        title_block.addWidget(self.description_label, 1, Qt.AlignmentFlag.AlignVCenter)

        self._action_layout = QHBoxLayout()
        self._action_layout.setContentsMargins(0, 0, 0, 0)
        self._action_layout.setSpacing(8)

        header_layout.addLayout(title_block, 1)
        header_layout.addLayout(self._action_layout)
        self._root_layout.addWidget(self.header_widget)

        self.body_widget = QWidget()
        self.body_widget.setObjectName("panelBody")
        self._body_layout = QVBoxLayout(self.body_widget)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(spacing)
        self._root_layout.addWidget(self.body_widget)

    def add_action(self, widget: QWidget) -> None:
        widget.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self._action_layout.addWidget(widget, 0, Qt.AlignmentFlag.AlignRight)

    def body_layout(self) -> QVBoxLayout:
        return self._body_layout

    def set_description(self, text: str) -> None:
        self.description_label.setText(text)
        self.description_label.setToolTip(text)
        self.description_label.setVisible(bool(text))
