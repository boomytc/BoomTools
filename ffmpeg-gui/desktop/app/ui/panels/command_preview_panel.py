from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QWidget

from desktop.app.ui.components import PanelFrame


class CommandPreviewPanel(PanelFrame):
    command_copied = Signal()

    def __init__(self) -> None:
        super().__init__("命令预览", density="compact")
        self._command = ""
        self.setObjectName("commandPreviewPanel")
        self.setMinimumHeight(82)
        self.setMaximumHeight(96)

        self.copy_button = QPushButton("复制")
        self.copy_button.setProperty("role", "quiet")
        self.copy_button.setToolTip("复制命令预览")
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(lambda _checked=False: self.copy_command())
        self.add_action(self.copy_button)

        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.preview_edit = QLineEdit()
        self.preview_edit.setObjectName("commandPreview")
        self.preview_edit.setReadOnly(True)
        self.preview_edit.setPlaceholderText("参数确认后显示 ffmpeg 命令预览")
        layout.addWidget(self.preview_edit, 1)
        self.body_layout().addWidget(row)

    def set_command(self, command: str) -> None:
        self._command = command
        self.preview_edit.setText(command)
        self.preview_edit.setCursorPosition(0)
        self.preview_edit.setToolTip(command)
        self.copy_button.setEnabled(bool(command.strip()))

    def set_batch_mode(self, enabled: bool) -> None:
        self.title_label.setText("命令模板预览" if enabled else "命令预览")
        self.preview_edit.setPlaceholderText(
            "参数确认后显示批量任务命令模板" if enabled else "参数确认后显示 ffmpeg 命令预览"
        )

    def copy_command(self) -> None:
        command = self._command.strip()
        if not command:
            return
        QGuiApplication.clipboard().setText(command)
        self.command_copied.emit()
