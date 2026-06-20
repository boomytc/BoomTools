from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from desktop.app.ui.widgets.path_picker import PathPicker


class RuntimePanel(QFrame):
    input_browse_requested = Signal()
    input_path_dropped = Signal(str)
    batch_files_requested = Signal()
    output_dir_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("runtimePanel")
        self.setAcceptDrops(True)
        self.setMinimumHeight(224)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        title_label = QLabel("输入媒体")
        title_label.setObjectName("sectionTitle")
        header_row.addWidget(title_label)
        header_row.addStretch(1)
        layout.addLayout(header_row)

        self.input_path_picker = PathPicker(placeholder="选择本机媒体文件", button_text="选择文件")
        self.input_path_picker.browse_requested.connect(self.input_browse_requested.emit)

        drop_area = QFrame()
        drop_area.setObjectName("fileDropArea")
        drop_area.setMinimumHeight(96)
        drop_layout = QVBoxLayout(drop_area)
        drop_layout.setContentsMargins(12, 12, 12, 12)
        drop_layout.setSpacing(6)
        drop_title = QLabel("选择或拖入本机视频/音频文件")
        drop_title.setObjectName("dropTitle")
        drop_hint = QLabel("MP4、WebM、MOV、AVI、MKV、GIF 等；文件只在本机处理。")
        drop_hint.setObjectName("mutedLabel")
        drop_layout.addWidget(drop_title)
        drop_layout.addWidget(drop_hint)
        drop_layout.addWidget(self.input_path_picker)
        layout.addWidget(drop_area)

        self.output_dir_picker = PathPicker(placeholder="输出目录，默认 data/outputs", button_text="输出目录")
        self.output_dir_picker.browse_requested.connect(self.output_dir_requested.emit)

        output_section = QFrame()
        output_section.setProperty("role", "panelSurface")
        output_layout = QVBoxLayout(output_section)
        output_layout.setContentsMargins(10, 10, 10, 10)
        output_layout.setSpacing(8)

        output_label = QLabel("输出目录")
        output_label.setObjectName("sectionTitle")
        self.batch_progress_label = QLabel("批处理：未启动")
        self.batch_progress_label.setObjectName("batchProgressLabel")
        self.batch_add_button = QPushButton("Batch 添加")
        self.batch_add_button.setProperty("role", "quiet")
        self.batch_add_button.clicked.connect(lambda _checked=False: self.batch_files_requested.emit())

        batch_row = QHBoxLayout()
        batch_row.setSpacing(8)
        batch_row.addWidget(self.batch_progress_label)
        batch_row.addStretch(1)
        batch_row.addWidget(self.batch_add_button)

        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_dir_picker)
        output_layout.addLayout(batch_row)
        layout.addWidget(output_section)

    def set_initial_paths(self, *, output_dir: Path) -> None:
        self.output_dir_picker.set_text(str(output_dir))

    def selected_input_path(self) -> Path | None:
        return self.input_path_picker.path()

    def selected_output_dir(self) -> Path | None:
        return self.output_dir_picker.path()

    def input_path_text(self) -> str:
        return self.input_path_picker.text()

    def set_input_path_text(self, path: str) -> None:
        self.input_path_picker.set_text(path)

    def set_output_dir_text(self, path: str) -> None:
        self.output_dir_picker.set_text(path)

    def set_batch_progress(self, current: int, total: int) -> None:
        if total == 0:
            self.batch_progress_label.setText("批处理：未启动")
            return
        self.batch_progress_label.setText(f"批处理：{current}/{total}")

    def set_busy(self, busy: bool) -> None:
        enabled = not busy
        self.input_path_picker.set_enabled(enabled)
        self.output_dir_picker.set_enabled(enabled)
        self.batch_add_button.setEnabled(enabled)

    def set_batch_add_enabled(self, enabled: bool) -> None:
        self.batch_add_button.setEnabled(enabled)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if not urls:
            super().dropEvent(event)
            return
        path = urls[0].toLocalFile()
        if not path:
            super().dropEvent(event)
            return
        self.input_path_picker.set_text(path)
        self.input_path_dropped.emit(path)
        event.acceptProposedAction()
