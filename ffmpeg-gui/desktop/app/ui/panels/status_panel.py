from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from shared.contracts import MediaInfo


class StatusPanel(QWidget):
    open_output_requested = Signal()
    open_output_dir_requested = Signal()
    copy_output_path_requested = Signal()

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        media_group = QGroupBox("媒体信息")
        media_layout = QVBoxLayout(media_group)
        self.media_info_view = QPlainTextEdit()
        self.media_info_view.setObjectName("mediaInfoView")
        self.media_info_view.setReadOnly(True)
        self.media_info_view.setPlainText("请选择本机媒体文件。")
        media_layout.addWidget(self.media_info_view)
        layout.addWidget(media_group, 2)

        progress_group = QGroupBox("任务进度")
        progress_layout = QVBoxLayout(progress_group)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.output_estimate_label = QLabel("输出大小保守估算：等待参数")
        self.output_estimate_label.setObjectName("outputEstimateLabel")
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setObjectName("outputPathEdit")
        self.output_path_edit.setReadOnly(True)
        self.command_preview = QPlainTextEdit()
        self.command_preview.setObjectName("commandPreview")
        self.command_preview.setReadOnly(True)
        self.command_preview.setFixedHeight(120)

        result_row = QHBoxLayout()
        self.open_output_button = QPushButton("打开输出文件")
        self.open_output_button.setProperty("role", "result")
        self.open_output_dir_button = QPushButton("打开输出目录")
        self.open_output_dir_button.setProperty("role", "result")
        self.copy_output_path_button = QPushButton("复制输出路径")
        self.copy_output_path_button.setProperty("role", "quiet")
        self.open_output_button.clicked.connect(lambda _checked=False: self.open_output_requested.emit())
        self.open_output_dir_button.clicked.connect(lambda _checked=False: self.open_output_dir_requested.emit())
        self.copy_output_path_button.clicked.connect(lambda _checked=False: self.copy_output_path_requested.emit())
        result_row.addWidget(self.open_output_button)
        result_row.addWidget(self.open_output_dir_button)
        result_row.addWidget(self.copy_output_path_button)

        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.output_path_edit)
        progress_layout.addWidget(self.output_estimate_label)
        progress_layout.addWidget(QLabel("命令预览"))
        progress_layout.addWidget(self.command_preview)
        progress_layout.addLayout(result_row)
        layout.addWidget(progress_group)

        log_group = QGroupBox("日志")
        log_layout = QVBoxLayout(log_group)
        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("logView")
        self.log_view.setReadOnly(True)
        log_layout.addWidget(self.log_view)
        layout.addWidget(log_group, 2)

        self.set_result_buttons_enabled(False)

    def set_media_info(self, media_info: MediaInfo | None) -> None:
        if media_info is None:
            self.media_info_view.setPlainText("请选择本机媒体文件。")
            return
        self.media_info_view.setPlainText(json.dumps(media_info.raw, ensure_ascii=False, indent=2))

    def set_progress(self, progress: float | None) -> None:
        if progress is None:
            self.progress_bar.setRange(0, 0)
            self.progress_bar.setFormat("运行中")
            return
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(int(progress * 100))
        self.progress_bar.setFormat("%p%")

    def reset_progress(self) -> None:
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")

    def append_log(self, line: str) -> None:
        self.log_view.appendPlainText(line)

    def clear_log(self) -> None:
        self.log_view.clear()

    def set_current_output(self, output_path: Path | None) -> None:
        self.output_path_edit.setText(str(output_path) if output_path else "")

    def set_command_preview(self, command: str) -> None:
        self.command_preview.setPlainText(command)

    def set_output_estimate(self, estimate: str) -> None:
        self.output_estimate_label.setText(estimate)

    def set_result_buttons_enabled(self, enabled: bool) -> None:
        self.open_output_button.setEnabled(enabled)
        self.open_output_dir_button.setEnabled(enabled)
        self.copy_output_path_button.setEnabled(enabled)
