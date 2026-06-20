from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from desktop.app.runtime.binaries import RuntimeHealth
from desktop.app.ui.widgets.path_picker import PathPicker


class RuntimePanel(QFrame):
    input_browse_requested = Signal()
    input_path_dropped = Signal(str)
    batch_files_requested = Signal()
    output_dir_requested = Signal()
    refresh_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("runtimePanel")
        self.setAcceptDrops(True)
        self.setMinimumHeight(260)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        title_label = QLabel("输入媒体")
        title_label.setObjectName("sectionTitle")
        self.health_label = QLabel("ffmpeg 未检查")
        self.health_label.setObjectName("healthLabel")
        header_row.addWidget(title_label)
        header_row.addStretch(1)
        header_row.addWidget(self.health_label)
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

        settings_section = QFrame()
        settings_section.setProperty("role", "panelSurface")
        settings_layout = QGridLayout(settings_section)
        settings_layout.setContentsMargins(10, 10, 10, 10)
        settings_layout.setHorizontalSpacing(8)
        settings_layout.setVerticalSpacing(7)

        self.ffmpeg_bin_edit = QLineEdit()
        self.ffmpeg_bin_edit.setPlaceholderText("ffmpeg")
        self.ffprobe_bin_edit = QLineEdit()
        self.ffprobe_bin_edit.setPlaceholderText("ffprobe")
        self.refresh_button = QPushButton("检查")
        self.refresh_button.setProperty("role", "quiet")
        self.refresh_button.clicked.connect(lambda _checked=False: self.refresh_requested.emit())
        self.advanced_paths_button = QPushButton("路径设置")
        self.advanced_paths_button.setCheckable(True)
        self.advanced_paths_button.setProperty("role", "quiet")
        self.advanced_paths_button.setToolTip("展开后可手动覆盖 ffmpeg / ffprobe 二进制路径")
        self.advanced_paths_button.toggled.connect(self._set_advanced_paths_visible)

        self.batch_progress_label = QLabel("批处理：未启动")
        self.batch_progress_label.setObjectName("batchProgressLabel")
        self.batch_add_button = QPushButton("Batch 添加")
        self.batch_add_button.setProperty("role", "quiet")
        self.batch_add_button.clicked.connect(lambda _checked=False: self.batch_files_requested.emit())

        settings_layout.addWidget(QLabel("输出"), 0, 0)
        settings_layout.addWidget(self.output_dir_picker, 0, 1, 1, 3)
        settings_layout.addWidget(QLabel("环境"), 1, 0)
        settings_layout.addWidget(self.refresh_button, 1, 1)
        settings_layout.addWidget(self.advanced_paths_button, 1, 2)
        settings_layout.addWidget(self.batch_add_button, 1, 3)
        settings_layout.addWidget(self.batch_progress_label, 2, 0, 1, 4)
        self.ffmpeg_bin_label = QLabel("ffmpeg")
        self.ffprobe_bin_label = QLabel("ffprobe")
        settings_layout.addWidget(self.ffmpeg_bin_label, 3, 0)
        settings_layout.addWidget(self.ffmpeg_bin_edit, 3, 1, 1, 3)
        settings_layout.addWidget(self.ffprobe_bin_label, 4, 0)
        settings_layout.addWidget(self.ffprobe_bin_edit, 4, 1, 1, 3)
        settings_layout.setColumnStretch(1, 1)
        layout.addWidget(settings_section)
        self._set_advanced_paths_visible(False)

    def set_initial_paths(self, *, ffmpeg_bin: str, ffprobe_bin: str, output_dir: Path) -> None:
        self.ffmpeg_bin_edit.setText(ffmpeg_bin)
        self.ffprobe_bin_edit.setText(ffprobe_bin)
        self.output_dir_picker.set_text(str(output_dir))

    def selected_ffmpeg_bin(self) -> str:
        return self.ffmpeg_bin_edit.text().strip() or "ffmpeg"

    def selected_ffprobe_bin(self) -> str:
        return self.ffprobe_bin_edit.text().strip() or "ffprobe"

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

    def set_runtime_health(self, health: RuntimeHealth) -> str:
        if health.ok:
            label = "ffmpeg/ffprobe 可用"
            tooltip = (
                f"ffmpeg: {health.ffmpeg_path or self.selected_ffmpeg_bin()}\n"
                f"ffprobe: {health.ffprobe_path or self.selected_ffprobe_bin()}"
            )
            self.health_label.setProperty("state", "ok")
        else:
            missing = []
            if not health.ffmpeg_available:
                missing.append("ffmpeg")
            if not health.ffprobe_available:
                missing.append("ffprobe")
            label = "不可用：" + ", ".join(missing)
            tooltip = label
            self.health_label.setProperty("state", "error")

        self.health_label.setText(label)
        self.health_label.setToolTip(tooltip)
        self.health_label.style().unpolish(self.health_label)
        self.health_label.style().polish(self.health_label)
        return health.ffmpeg_version or ""

    def set_batch_progress(self, current: int, total: int) -> None:
        if total == 0:
            self.batch_progress_label.setText("批处理：未启动")
            return
        self.batch_progress_label.setText(f"批处理：{current}/{total}")

    def set_busy(self, busy: bool) -> None:
        enabled = not busy
        self.input_path_picker.set_enabled(enabled)
        self.output_dir_picker.set_enabled(enabled)
        self.ffmpeg_bin_edit.setEnabled(enabled)
        self.ffprobe_bin_edit.setEnabled(enabled)
        self.refresh_button.setEnabled(enabled)
        self.batch_add_button.setEnabled(enabled)

    def set_batch_add_enabled(self, enabled: bool) -> None:
        self.batch_add_button.setEnabled(enabled)

    def _set_advanced_paths_visible(self, visible: bool) -> None:
        self.ffmpeg_bin_label.setVisible(visible)
        self.ffmpeg_bin_edit.setVisible(visible)
        self.ffprobe_bin_label.setVisible(visible)
        self.ffprobe_bin_edit.setVisible(visible)

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
