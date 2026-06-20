from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from desktop.app.ui.widgets.path_picker import PathPicker
from shared.contracts import MediaInfo


class RuntimePanel(QFrame):
    input_browse_requested = Signal()
    input_path_dropped = Signal(str)
    batch_files_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("runtimePanel")
        self.setAcceptDrops(True)
        self.setMinimumHeight(180)

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

        self.media_summary_panel = QFrame()
        self.media_summary_panel.setObjectName("mediaSummaryPanel")
        self.media_summary_panel.setProperty("role", "panelSurface")
        summary_layout = QVBoxLayout(self.media_summary_panel)
        summary_layout.setContentsMargins(10, 10, 10, 10)
        summary_layout.setSpacing(8)
        summary_header = QHBoxLayout()
        summary_title = QLabel("媒体摘要")
        summary_title.setObjectName("sectionTitle")
        self.media_summary_hint = QLabel("")
        self.media_summary_hint.setObjectName("mutedLabel")
        summary_header.addWidget(summary_title)
        summary_header.addStretch(1)
        summary_header.addWidget(self.media_summary_hint)
        self.media_chip_grid = QGridLayout()
        self.media_chip_grid.setHorizontalSpacing(6)
        self.media_chip_grid.setVerticalSpacing(6)
        for column in range(4):
            self.media_chip_grid.setColumnStretch(column, 1)
        summary_layout.addLayout(summary_header)
        summary_layout.addLayout(self.media_chip_grid)
        layout.addWidget(self.media_summary_panel)
        self.media_summary_panel.setVisible(False)

        batch_section = QFrame()
        batch_section.setProperty("role", "panelSurface")
        batch_layout = QHBoxLayout(batch_section)
        batch_layout.setContentsMargins(10, 10, 10, 10)
        batch_layout.setSpacing(8)

        self.batch_progress_label = QLabel("批处理：未启动")
        self.batch_progress_label.setObjectName("batchProgressLabel")
        self.batch_add_button = QPushButton("Batch 添加")
        self.batch_add_button.setProperty("role", "quiet")
        self.batch_add_button.clicked.connect(lambda _checked=False: self.batch_files_requested.emit())

        batch_layout.addWidget(self.batch_progress_label)
        batch_layout.addStretch(1)
        batch_layout.addWidget(self.batch_add_button)
        layout.addWidget(batch_section)

    def selected_input_path(self) -> Path | None:
        return self.input_path_picker.path()

    def input_path_text(self) -> str:
        return self.input_path_picker.text()

    def set_input_path_text(self, path: str) -> None:
        self.input_path_picker.set_text(path)

    def set_media_info(self, media_info: MediaInfo | None) -> None:
        self._clear_media_chips()
        if media_info is None:
            self.media_summary_panel.setVisible(False)
            return
        self.media_summary_panel.setVisible(True)
        if media_info.has_error:
            self.media_summary_hint.setText("读取失败")
            self._add_media_chip("无法读取媒体信息", state="error", tooltip=media_info.error_message or "")
            return

        self.media_summary_hint.setText("已读取")
        chips = self._media_summary_chips(media_info)
        if not chips:
            self._add_media_chip("媒体信息不可用", state="muted")
            return
        for text, tooltip in chips:
            self._add_media_chip(text, tooltip=tooltip)

    def set_batch_progress(self, current: int, total: int) -> None:
        if total == 0:
            self.batch_progress_label.setText("批处理：未启动")
            return
        self.batch_progress_label.setText(f"批处理：{current}/{total}")

    def set_busy(self, busy: bool) -> None:
        enabled = not busy
        self.input_path_picker.set_enabled(enabled)
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

    def _clear_media_chips(self) -> None:
        while self.media_chip_grid.count():
            item = self.media_chip_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.media_summary_hint.setText("")

    def _add_media_chip(self, text: str, *, state: str = "ok", tooltip: str = "") -> None:
        label = QLabel(text)
        label.setObjectName("mediaChip")
        label.setProperty("state", state)
        label.setToolTip(tooltip or text)
        label.setMinimumHeight(24)
        label.setWordWrap(False)
        index = self.media_chip_grid.count()
        self.media_chip_grid.addWidget(label, index // 4, index % 4)

    def _media_summary_chips(self, media_info: MediaInfo) -> list[tuple[str, str]]:
        raw = media_info.raw
        format_info = raw.get("format", {}) if isinstance(raw.get("format"), dict) else {}
        streams = raw.get("streams", []) if isinstance(raw.get("streams"), list) else []
        video_stream = self._first_stream(streams, "video")
        audio_stream = self._first_stream(streams, "audio")

        chips: list[tuple[str, str]] = []
        duration = media_info.duration_seconds or self._float_value(format_info.get("duration"))
        if duration:
            chips.append((f"时长 {self._format_duration(duration)}", f"{duration:.2f} 秒"))
        if video_stream:
            width = self._int_value(video_stream.get("width"))
            height = self._int_value(video_stream.get("height"))
            if width and height:
                chips.append((f"{width}×{height}", "视频分辨率"))
            fps = self._frame_rate(video_stream)
            if fps:
                chips.append((f"{fps:g} fps", "视频帧率"))
            video_codec = video_stream.get("codec_name")
            if video_codec:
                chips.append((f"视频 {video_codec}", "视频编码"))
        if audio_stream:
            audio_codec = audio_stream.get("codec_name")
            if audio_codec:
                chips.append((f"音频 {audio_codec}", "音频编码"))
        format_name = str(format_info.get("format_name") or "").split(",", maxsplit=1)[0]
        if format_name:
            chips.append((f"格式 {format_name}", "容器格式"))
        size = self._int_value(format_info.get("size"))
        if size:
            chips.append((f"大小 {self._format_bytes(size)}", "文件大小"))
        return chips

    def _first_stream(self, streams: list[Any], codec_type: str) -> dict[str, Any]:
        for stream in streams:
            if isinstance(stream, dict) and stream.get("codec_type") == codec_type:
                return stream
        return {}

    def _frame_rate(self, stream: dict[str, Any]) -> float | None:
        value = stream.get("avg_frame_rate") or stream.get("r_frame_rate")
        if not value:
            return None
        parts = str(value).split("/")
        try:
            if len(parts) == 2:
                denominator = float(parts[1])
                return float(parts[0]) / denominator if denominator else None
            return float(parts[0])
        except (TypeError, ValueError):
            return None

    def _float_value(self, value: object) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if number > 0 else None

    def _int_value(self, value: object) -> int | None:
        try:
            number = int(float(value))
        except (TypeError, ValueError):
            return None
        return number if number > 0 else None

    def _format_duration(self, duration_seconds: float) -> str:
        total = int(round(duration_seconds))
        hours, remainder = divmod(total, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    def _format_bytes(self, size: int) -> str:
        value = float(size)
        for unit in ("B", "KB", "MB", "GB"):
            if value < 1024 or unit == "GB":
                return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
            value /= 1024
        return f"{size} B"
