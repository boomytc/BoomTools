from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QSizePolicy, QWidget


class PathPicker(QWidget):
    browse_requested = Signal()
    text_changed = Signal(str)

    def __init__(
        self,
        *,
        placeholder: str = "",
        button_text: str = "选择",
        read_only: bool = False,
    ) -> None:
        super().__init__()
        self.setObjectName("pathPicker")
        self.setProperty("role", "pathPicker")
        self.setMinimumHeight(40)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 1, 0, 1)
        layout.setSpacing(8)

        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText(placeholder)
        self.line_edit.setReadOnly(read_only)
        self.line_edit.textChanged.connect(self._on_text_changed)

        self.browse_button = QPushButton(button_text)
        self.browse_button.setProperty("role", "pathBrowseButton")
        self.browse_button.clicked.connect(lambda _checked=False: self.browse_requested.emit())

        layout.addWidget(self.line_edit, 1)
        layout.addWidget(self.browse_button)

    def text(self) -> str:
        return self.line_edit.text()

    def set_text(self, text: str) -> None:
        self.line_edit.setText(text)

    def path(self) -> Path | None:
        text = self.text().strip()
        return Path(text) if text else None

    def set_placeholder(self, text: str) -> None:
        self.line_edit.setPlaceholderText(text)

    def set_button_text(self, text: str) -> None:
        self.browse_button.setText(text)

    def set_enabled(self, enabled: bool) -> None:
        super().setEnabled(enabled)
        self.line_edit.setEnabled(enabled)
        self.browse_button.setEnabled(enabled)

    def set_read_only(self, read_only: bool) -> None:
        self.line_edit.setReadOnly(read_only)

    def _on_text_changed(self, text: str) -> None:
        self.line_edit.setToolTip(text)
        self.text_changed.emit(text)
