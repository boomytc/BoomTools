from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QLineEdit, QPushButton

from desktop.app.runtime.binaries import RuntimeHealth
from desktop.app.ui.widgets.path_picker import PathPicker


class RuntimePanel(QFrame):
    input_browse_requested = Signal()
    batch_files_requested = Signal()
    output_dir_requested = Signal()
    refresh_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("topPanel")

        layout = QGridLayout(self)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)

        self.input_path_picker = PathPicker(placeholder="选择本机媒体文件", button_text="选择文件")
        self.input_path_picker.browse_requested.connect(self.input_browse_requested.emit)

        self.output_dir_picker = PathPicker(placeholder="输出目录，默认 data/outputs", button_text="输出目录")
        self.output_dir_picker.browse_requested.connect(self.output_dir_requested.emit)

        self.ffmpeg_bin_edit = QLineEdit()
        self.ffmpeg_bin_edit.setPlaceholderText("ffmpeg")
        self.ffprobe_bin_edit = QLineEdit()
        self.ffprobe_bin_edit.setPlaceholderText("ffprobe")
        self.refresh_button = QPushButton("检查")
        self.refresh_button.clicked.connect(lambda _checked=False: self.refresh_requested.emit())

        self.health_label = QLabel("等待检查 ffmpeg/ffprobe")
        self.health_label.setObjectName("healthLabel")
        self.batch_progress_label = QLabel("批处理：未启动")
        self.batch_progress_label.setObjectName("batchProgressLabel")
        self.batch_add_button = QPushButton("添加多个文件到队列")
        self.batch_add_button.setProperty("role", "quiet")
        self.batch_add_button.clicked.connect(lambda _checked=False: self.batch_files_requested.emit())

        layout.addWidget(QLabel("输入"), 0, 0)
        layout.addWidget(self.input_path_picker, 0, 1, 1, 4)
        layout.addWidget(self.batch_add_button, 0, 5)
        layout.addWidget(QLabel("输出"), 1, 0)
        layout.addWidget(self.output_dir_picker, 1, 1, 1, 4)
        layout.addWidget(QLabel("ffmpeg"), 2, 0)
        layout.addWidget(self.ffmpeg_bin_edit, 2, 1)
        layout.addWidget(QLabel("ffprobe"), 2, 2)
        layout.addWidget(self.ffprobe_bin_edit, 2, 3)
        layout.addWidget(self.refresh_button, 2, 4)
        layout.addWidget(self.health_label, 3, 0, 1, 5)
        layout.addWidget(self.batch_progress_label, 4, 0, 1, 5)
        layout.setColumnStretch(1, 2)
        layout.setColumnStretch(3, 2)

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
            label = f"ffmpeg/ffprobe 可用：{health.ffmpeg_path or self.selected_ffmpeg_bin()}"
            self.health_label.setProperty("state", "ok")
        else:
            missing = []
            if not health.ffmpeg_available:
                missing.append("ffmpeg")
            if not health.ffprobe_available:
                missing.append("ffprobe")
            label = "不可用：" + ", ".join(missing)
            self.health_label.setProperty("state", "error")

        self.health_label.setText(label)
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
