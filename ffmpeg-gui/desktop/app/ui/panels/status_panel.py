from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop.app.ui.widgets.path_picker import PathPicker


class StatusPanel(QWidget):
    output_dir_requested = Signal()
    open_output_requested = Signal()
    open_output_dir_requested = Signal()
    copy_output_path_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("statusPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setMinimumHeight(218)
        self.setMaximumHeight(232)

        progress_group = QGroupBox("输出")
        progress_group.setObjectName("outputPanel")
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setSpacing(6)
        self.output_dir_picker = PathPicker(placeholder="输出目录，默认 data/outputs", button_text="选择")
        self.output_dir_picker.browse_requested.connect(self.output_dir_requested.emit)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setFormat("等待任务")
        self.output_estimate_label = QLabel("输出大小保守估算：等待参数")
        self.output_estimate_label.setObjectName("outputEstimateLabel")
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setObjectName("outputPathEdit")
        self.output_path_edit.setReadOnly(True)
        self.output_path_edit.setPlaceholderText("任务完成后显示输出文件路径")
        self.command_preview = QLineEdit()
        self.command_preview.setObjectName("commandPreview")
        self.command_preview.setReadOnly(True)
        self.command_preview.setPlaceholderText("参数确认后显示 ffmpeg 命令预览")

        self.open_output_button = QPushButton("打开")
        self.open_output_button.setProperty("role", "result")
        self.open_output_dir_button = QPushButton("目录")
        self.open_output_dir_button.setProperty("role", "result")
        self.copy_output_path_button = QPushButton("复制")
        self.copy_output_path_button.setProperty("role", "quiet")
        self.open_output_button.setToolTip("打开输出文件")
        self.open_output_dir_button.setToolTip("打开输出目录")
        self.copy_output_path_button.setToolTip("复制输出文件路径")
        self.open_output_button.clicked.connect(lambda _checked=False: self.open_output_requested.emit())
        self.open_output_dir_button.clicked.connect(lambda _checked=False: self.open_output_dir_requested.emit())
        self.copy_output_path_button.clicked.connect(lambda _checked=False: self.copy_output_path_requested.emit())

        output_dir_row = QHBoxLayout()
        output_dir_row.setSpacing(8)
        output_dir_label = QLabel("目标目录")
        output_dir_label.setObjectName("subsectionTitle")
        output_dir_row.addWidget(output_dir_label)
        output_dir_row.addWidget(self.output_dir_picker, 1)
        progress_layout.addLayout(output_dir_row)
        progress_layout.addWidget(self.progress_bar)

        output_file_row = QHBoxLayout()
        output_file_row.setSpacing(8)
        output_file_label = QLabel("输出文件")
        output_file_label.setObjectName("subsectionTitle")
        output_file_row.addWidget(output_file_label)
        output_file_row.addWidget(self.output_path_edit, 1)
        output_file_row.addWidget(self.open_output_button)
        output_file_row.addWidget(self.open_output_dir_button)
        output_file_row.addWidget(self.copy_output_path_button)
        progress_layout.addLayout(output_file_row)
        progress_layout.addWidget(self.output_estimate_label)
        command_label = QLabel("命令预览")
        command_label.setObjectName("subsectionTitle")
        progress_layout.addWidget(command_label)
        progress_layout.addWidget(self.command_preview)
        layout.addWidget(progress_group, 1)

        self.set_result_buttons_enabled(False)

    def selected_output_dir(self) -> Path | None:
        return self.output_dir_picker.path()

    def set_output_dir_text(self, path: str) -> None:
        self.output_dir_picker.set_text(path)

    def set_busy(self, busy: bool) -> None:
        self.output_dir_picker.set_enabled(not busy)

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

    def set_current_output(self, output_path: Path | None) -> None:
        output_text = str(output_path) if output_path else ""
        self.output_path_edit.setText(output_text)
        self.output_path_edit.setToolTip(output_text)

    def set_command_preview(self, command: str) -> None:
        self.command_preview.setText(command)
        self.command_preview.setCursorPosition(0)
        self.command_preview.setToolTip(command)

    def set_output_estimate(self, estimate: str) -> None:
        self.output_estimate_label.setText(estimate)

    def set_result_buttons_enabled(self, enabled: bool) -> None:
        self.open_output_button.setEnabled(enabled)
        self.open_output_dir_button.setEnabled(enabled)
        self.copy_output_path_button.setEnabled(enabled)
