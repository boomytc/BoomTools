from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from desktop.app.runtime.binaries import RuntimeHealth


class SettingsDialog(QDialog):
    check_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsDialog")
        self.setWindowTitle("设置")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumWidth(560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        header = QVBoxLayout()
        header.setSpacing(6)
        title = QLabel("设置")
        title.setObjectName("dialogTitle")
        description = QLabel("配置本机 ffmpeg 环境。通常只需要在首次使用或自动检测失败时调整。")
        description.setObjectName("settingsDescription")
        description.setWordWrap(True)
        header.addWidget(title)
        header.addWidget(description)
        layout.addLayout(header)

        status_panel = QFrame()
        status_panel.setObjectName("settingsStatusPanel")
        status_panel.setProperty("role", "panelSurface")
        status_layout = QHBoxLayout(status_panel)
        status_layout.setContentsMargins(12, 10, 12, 10)
        status_layout.setSpacing(10)
        status_title = QLabel("FFmpeg 环境")
        status_title.setObjectName("sectionTitle")
        self.health_label = QLabel("未检查")
        self.health_label.setObjectName("healthLabel")
        self.health_label.setProperty("state", "idle")
        self.version_label = QLabel("点击“保存并检查”检测当前路径。")
        self.version_label.setObjectName("settingsDescription")
        status_layout.addWidget(status_title)
        status_layout.addWidget(self.health_label)
        status_layout.addWidget(self.version_label, 1)
        layout.addWidget(status_panel)

        form_panel = QFrame()
        form_panel.setObjectName("settingsFormPanel")
        form_panel.setProperty("role", "panelSurface")
        form_layout = QGridLayout(form_panel)
        form_layout.setContentsMargins(12, 12, 12, 12)
        form_layout.setHorizontalSpacing(10)
        form_layout.setVerticalSpacing(10)

        self.ffmpeg_bin_edit = QLineEdit()
        self.ffmpeg_bin_edit.setObjectName("binaryPathEdit")
        self.ffmpeg_bin_edit.setPlaceholderText("ffmpeg")
        self.ffprobe_bin_edit = QLineEdit()
        self.ffprobe_bin_edit.setObjectName("binaryPathEdit")
        self.ffprobe_bin_edit.setPlaceholderText("ffprobe")

        self.ffmpeg_browse_button = QPushButton("选择")
        self.ffmpeg_browse_button.setProperty("role", "pathBrowseButton")
        self.ffprobe_browse_button = QPushButton("选择")
        self.ffprobe_browse_button.setProperty("role", "pathBrowseButton")
        self.ffmpeg_browse_button.clicked.connect(
            lambda _checked=False: self._browse_binary(self.ffmpeg_bin_edit, "选择 ffmpeg 可执行文件")
        )
        self.ffprobe_browse_button.clicked.connect(
            lambda _checked=False: self._browse_binary(self.ffprobe_bin_edit, "选择 ffprobe 可执行文件")
        )

        hint = QLabel("可填写命令名，也可选择本机可执行文件的绝对路径。")
        hint.setObjectName("settingsDescription")
        hint.setWordWrap(True)

        form_layout.addWidget(QLabel("ffmpeg"), 0, 0)
        form_layout.addWidget(self.ffmpeg_bin_edit, 0, 1)
        form_layout.addWidget(self.ffmpeg_browse_button, 0, 2)
        form_layout.addWidget(QLabel("ffprobe"), 1, 0)
        form_layout.addWidget(self.ffprobe_bin_edit, 1, 1)
        form_layout.addWidget(self.ffprobe_browse_button, 1, 2)
        form_layout.addWidget(hint, 2, 1, 1, 2)
        form_layout.setColumnStretch(1, 1)
        layout.addWidget(form_panel)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self.check_button = QPushButton("保存并检查")
        self.check_button.setObjectName("primaryButton")
        self.close_button = QPushButton("关闭")
        self.close_button.setProperty("role", "quiet")
        self.check_button.clicked.connect(lambda _checked=False: self.check_requested.emit())
        self.close_button.clicked.connect(self.close)
        button_row.addWidget(self.check_button)
        button_row.addWidget(self.close_button)
        layout.addLayout(button_row)

    def set_initial_paths(self, *, ffmpeg_bin: str, ffprobe_bin: str) -> None:
        self.ffmpeg_bin_edit.setText(ffmpeg_bin)
        self.ffprobe_bin_edit.setText(ffprobe_bin)

    def selected_ffmpeg_bin(self) -> str:
        return self.ffmpeg_bin_edit.text().strip() or "ffmpeg"

    def selected_ffprobe_bin(self) -> str:
        return self.ffprobe_bin_edit.text().strip() or "ffprobe"

    def set_runtime_health(self, health: RuntimeHealth) -> str:
        if health.ok:
            label = "可用"
            detail = (
                f"ffmpeg: {health.ffmpeg_path or self.selected_ffmpeg_bin()}\n"
                f"ffprobe: {health.ffprobe_path or self.selected_ffprobe_bin()}"
            )
            self.health_label.setProperty("state", "ok")
            self.version_label.setText(health.ffmpeg_version or "当前路径检测通过。")
        else:
            missing = []
            if not health.ffmpeg_available:
                missing.append("ffmpeg")
            if not health.ffprobe_available:
                missing.append("ffprobe")
            label = "不可用"
            detail = "缺少：" + "、".join(missing) if missing else "当前路径检测失败。"
            self.health_label.setProperty("state", "error")
            self.version_label.setText(detail)

        self.health_label.setText(label)
        self.health_label.setToolTip(detail)
        self.health_label.style().unpolish(self.health_label)
        self.health_label.style().polish(self.health_label)
        return health.ffmpeg_version or ""

    def set_busy(self, busy: bool) -> None:
        enabled = not busy
        self.ffmpeg_bin_edit.setEnabled(enabled)
        self.ffprobe_bin_edit.setEnabled(enabled)
        self.ffmpeg_browse_button.setEnabled(enabled)
        self.ffprobe_browse_button.setEnabled(enabled)
        self.check_button.setEnabled(enabled)

    def _browse_binary(self, line_edit: QLineEdit, title: str) -> None:
        start_dir = self._start_dir_for_path(line_edit.text())
        path, _ = QFileDialog.getOpenFileName(self, title, start_dir)
        if path:
            line_edit.setText(path)

    def _start_dir_for_path(self, path_text: str) -> str:
        if not path_text.strip():
            return str(Path.home())
        path = Path(path_text).expanduser()
        if path.exists():
            if path.is_dir():
                return str(path)
            return str(path.parent)
        return str(Path.home())
