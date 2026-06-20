from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from desktop.app.ui.widgets.path_picker import PathPicker

_OUTPUT_LABEL_WIDTH = 52


class StatusPanel(QWidget):
    output_dir_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("statusPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setMinimumHeight(78)
        self.setMaximumHeight(96)

        output_group = QGroupBox("输出")
        output_group.setObjectName("outputPanel")
        output_layout = QVBoxLayout(output_group)
        output_layout.setSpacing(0)
        self.output_dir_picker = PathPicker(placeholder="输出目录，默认 data/outputs", button_text="选择")
        self.output_dir_picker.browse_requested.connect(self.output_dir_requested.emit)

        output_dir_row = QHBoxLayout()
        output_dir_row.setSpacing(8)
        output_dir_label = QLabel("目标目录")
        output_dir_label.setObjectName("subsectionTitle")
        output_dir_label.setFixedWidth(_OUTPUT_LABEL_WIDTH)
        output_dir_row.addWidget(output_dir_label)
        output_dir_row.addWidget(self.output_dir_picker, 1)
        output_layout.addLayout(output_dir_row)
        layout.addWidget(output_group, 1)

    def selected_output_dir(self) -> Path | None:
        return self.output_dir_picker.path()

    def set_output_dir_text(self, path: str) -> None:
        self.output_dir_picker.set_text(path)

    def set_busy(self, busy: bool) -> None:
        self.output_dir_picker.set_enabled(not busy)
