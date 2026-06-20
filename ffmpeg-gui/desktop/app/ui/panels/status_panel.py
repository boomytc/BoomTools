from __future__ import annotations

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

from desktop.app.ui.widgets.path_picker import PathPicker


class StatusPanel(QWidget):
    output_dir_requested = Signal()
    open_output_requested = Signal()
    open_output_dir_requested = Signal()
    copy_output_path_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("statusPanel")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self.setMinimumHeight(226)
        self.setMaximumHeight(240)

        progress_group = QGroupBox("输出")
        progress_group.setObjectName("outputPanel")
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setSpacing(8)
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
        self.command_preview = QPlainTextEdit()
        self.command_preview.setObjectName("commandPreview")
        self.command_preview.setReadOnly(True)
        self.command_preview.setMinimumHeight(42)
        self.command_preview.setMaximumHeight(48)

        command_row = QHBoxLayout()
        self.open_output_button = QPushButton("打开文件")
        self.open_output_button.setProperty("role", "result")
        self.open_output_dir_button = QPushButton("打开目录")
        self.open_output_dir_button.setProperty("role", "result")
        self.copy_output_path_button = QPushButton("复制路径")
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
        progress_layout.addWidget(self.output_path_edit)
        progress_layout.addWidget(self.output_estimate_label)
        command_label = QLabel("命令预览")
        command_label.setObjectName("subsectionTitle")
        command_row.addWidget(command_label)
        command_row.addStretch(1)
        command_row.addWidget(self.open_output_button)
        command_row.addWidget(self.open_output_dir_button)
        command_row.addWidget(self.copy_output_path_button)
        progress_layout.addLayout(command_row)
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
        self.output_path_edit.setText(str(output_path) if output_path else "")

    def set_command_preview(self, command: str) -> None:
        self.command_preview.setPlainText(command)

    def set_output_estimate(self, estimate: str) -> None:
        self.output_estimate_label.setText(estimate)

    def set_result_buttons_enabled(self, enabled: bool) -> None:
        self.open_output_button.setEnabled(enabled)
        self.open_output_dir_button.setEnabled(enabled)
        self.copy_output_path_button.setEnabled(enabled)
