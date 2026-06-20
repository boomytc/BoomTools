from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop.app.ui.widgets.path_picker import PathPicker

_OUTPUT_LABEL_WIDTH = 52


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
        self.setMinimumHeight(168)
        self.setMaximumHeight(184)

        output_group = QGroupBox("输出")
        output_group.setObjectName("outputPanel")
        output_layout = QVBoxLayout(output_group)
        output_layout.setSpacing(11)
        self.output_dir_picker = PathPicker(placeholder="输出目录，默认 data/outputs", button_text="选择")
        self.output_dir_picker.browse_requested.connect(self.output_dir_requested.emit)
        self.output_estimate_label = QLabel("输出大小保守估算：等待参数")
        self.output_estimate_label.setObjectName("outputEstimateLabel")
        self.output_estimate_label.setContentsMargins(0, 2, 0, 0)
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setObjectName("outputPathEdit")
        self.output_path_edit.setReadOnly(True)
        self.output_path_edit.setPlaceholderText("任务完成后显示输出文件路径")

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
        output_dir_label.setFixedWidth(_OUTPUT_LABEL_WIDTH)
        output_dir_row.addWidget(output_dir_label)
        output_dir_row.addWidget(self.output_dir_picker, 1)
        output_layout.addLayout(output_dir_row)

        output_file_row = QHBoxLayout()
        output_file_row.setSpacing(8)
        output_file_label = QLabel("输出文件")
        output_file_label.setObjectName("subsectionTitle")
        output_file_label.setFixedWidth(_OUTPUT_LABEL_WIDTH)
        output_file_row.addWidget(output_file_label)
        output_file_row.addWidget(self.output_path_edit, 1)
        output_file_row.addWidget(self.open_output_button)
        output_file_row.addWidget(self.open_output_dir_button)
        output_file_row.addWidget(self.copy_output_path_button)
        output_layout.addLayout(output_file_row)
        output_layout.addWidget(self.output_estimate_label)
        layout.addWidget(output_group, 1)

        self.set_result_buttons_enabled(False)

    def selected_output_dir(self) -> Path | None:
        return self.output_dir_picker.path()

    def set_output_dir_text(self, path: str) -> None:
        self.output_dir_picker.set_text(path)

    def set_busy(self, busy: bool) -> None:
        self.output_dir_picker.set_enabled(not busy)

    def set_current_output(self, output_path: Path | None) -> None:
        output_text = str(output_path) if output_path else ""
        self.output_path_edit.setText(output_text)
        self.output_path_edit.setToolTip(output_text)

    def set_output_estimate(self, estimate: str) -> None:
        self.output_estimate_label.setText(estimate)

    def set_result_buttons_enabled(self, enabled: bool) -> None:
        self.open_output_button.setEnabled(enabled)
        self.open_output_dir_button.setEnabled(enabled)
        self.copy_output_path_button.setEnabled(enabled)
