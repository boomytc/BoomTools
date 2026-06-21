from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QSizePolicy, QWidget


class PanelActionBar(QWidget):
    def __init__(self, *, alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignRight, density: str = "compact") -> None:
        super().__init__()
        self.setObjectName("panelActionBar")
        self.setProperty("density", density)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self._alignment = alignment

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8 if density == "compact" else 10)
        if alignment == Qt.AlignmentFlag.AlignRight:
            self._layout.addStretch(1)

    def add_button(
        self,
        text: str,
        *,
        role: str = "quiet",
        object_name: str = "",
        enabled: bool = True,
    ) -> QPushButton:
        button = QPushButton(text)
        if object_name:
            button.setObjectName(object_name)
        if role == "primary" and not object_name:
            button.setObjectName("primaryButton")
        elif role:
            button.setProperty("role", role)
        button.setProperty("density", str(self.property("density") or "compact"))
        button.setEnabled(enabled)
        if self._alignment == Qt.AlignmentFlag.AlignRight:
            self._layout.insertWidget(max(0, self._layout.count() - 1), button)
        else:
            self._layout.addWidget(button)
        return button

    def add_widget(self, widget: QWidget) -> None:
        if self._alignment == Qt.AlignmentFlag.AlignRight:
            self._layout.insertWidget(max(0, self._layout.count() - 1), widget)
        else:
            self._layout.addWidget(widget)
