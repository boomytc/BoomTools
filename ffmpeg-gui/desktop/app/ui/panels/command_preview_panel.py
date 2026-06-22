from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QGuiApplication, QTextCursor
from PySide6.QtWidgets import QHBoxLayout, QPlainTextEdit, QPushButton, QWidget

from desktop.app.ui.components import PanelFrame


COMMAND_PREVIEW_COMPACT_HEIGHT = (72, 92)
COMMAND_PREVIEW_EXPANDED_HEIGHT = (176, 260)


class CommandPreviewPanel(PanelFrame):
    command_copied = Signal()
    height_mode_changed = Signal()

    def __init__(self) -> None:
        super().__init__("命令预览", density="compact")
        self._command = ""
        self._expanded = False
        self.setObjectName("commandPreviewPanel")
        self._sync_preview_height()

        self.copy_button = QPushButton("复制")
        self.copy_button.setProperty("role", "quiet")
        self.copy_button.setToolTip("复制命令预览")
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(lambda _checked=False: self.copy_command())
        self.add_action(self.copy_button)

        self.expand_button = QPushButton("展开")
        self.expand_button.setCheckable(True)
        self.expand_button.setProperty("role", "quiet")
        self.expand_button.setToolTip("展开为多行命令预览")
        self.expand_button.clicked.connect(lambda checked=False: self.set_expanded(bool(checked)))
        self.add_action(self.expand_button)

        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.preview_edit = QPlainTextEdit()
        self.preview_edit.setObjectName("commandPreview")
        self.preview_edit.setReadOnly(True)
        self.preview_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.preview_edit.setPlaceholderText("参数确认后显示 ffmpeg 命令预览")
        layout.addWidget(self.preview_edit, 1)
        self.body_layout().addWidget(row)

    def set_command(self, command: str) -> None:
        self._command = command
        self.preview_edit.setPlainText(command)
        self.preview_edit.moveCursor(QTextCursor.MoveOperation.Start)
        self.preview_edit.setToolTip(command)
        self.copy_button.setEnabled(bool(command.strip()))

    def set_batch_mode(self, enabled: bool) -> None:
        self.title_label.setText("命令模板预览" if enabled else "命令预览")
        self.preview_edit.setPlaceholderText(
            "参数确认后显示批量任务命令模板" if enabled else "参数确认后显示 ffmpeg 命令预览"
        )

    def set_output_estimate(self, estimate: str) -> None:
        self.set_description(estimate)

    def copy_command(self) -> None:
        command = self._command.strip()
        if not command:
            return
        QGuiApplication.clipboard().setText(command)
        self.command_copied.emit()

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self.expand_button.setChecked(expanded)
        self.expand_button.setText("收起" if expanded else "展开")
        self.expand_button.setToolTip("收起为紧凑命令预览" if expanded else "展开为多行命令预览")
        self._sync_preview_height()
        self.height_mode_changed.emit()

    def is_expanded(self) -> bool:
        return self._expanded

    def _sync_preview_height(self) -> None:
        minimum, maximum = COMMAND_PREVIEW_EXPANDED_HEIGHT if self._expanded else COMMAND_PREVIEW_COMPACT_HEIGHT
        self.setMinimumHeight(minimum)
        self.setMaximumHeight(maximum)
        self.updateGeometry()
