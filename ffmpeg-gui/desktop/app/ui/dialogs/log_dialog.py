from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout


class LogDialog(QDialog):
    cleared = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("logDialog")
        self.setWindowTitle("FFmpeg Log")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(760, 460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("FFmpeg Log")
        title.setObjectName("dialogTitle")
        self.copy_button = QPushButton("复制")
        self.copy_button.setProperty("role", "quiet")
        self.clear_button = QPushButton("Clear")
        self.clear_button.setProperty("role", "quiet")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.copy_button)
        header.addWidget(self.clear_button)
        layout.addLayout(header)

        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("logView")
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("运行任务后会显示 FFmpeg 命令和输出。")
        layout.addWidget(self.log_view, 1)

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        self.close_button = QPushButton("关闭")
        self.close_button.setProperty("role", "quiet")
        close_row.addWidget(self.close_button)
        layout.addLayout(close_row)

        self.copy_button.clicked.connect(self.copy_log)
        self.clear_button.clicked.connect(self.clear_log)
        self.close_button.clicked.connect(self.close)

    def append_log(self, line: str) -> None:
        self.log_view.appendPlainText(line)

    def clear_log(self) -> None:
        self.log_view.clear()
        self.cleared.emit()

    def copy_log(self) -> None:
        text = self.log_view.toPlainText()
        if text:
            QGuiApplication.clipboard().setText(text)
