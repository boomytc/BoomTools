from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget

from desktop.app.ui.components import PanelActionBar, PanelFrame, SegmentOption, SegmentedToggle
from desktop.app.ui.widgets.media_player_widget import MediaPlayerWidget
from shared.contracts import MediaInfo, Operation, TaskRecord

AUDIO_PREVIEW_EXTENSIONS = {
    ".aac",
    ".aif",
    ".aiff",
    ".flac",
    ".m4a",
    ".mp3",
    ".ogg",
    ".opus",
    ".wav",
    ".wma",
}


class MediaPreviewPanel(PanelFrame):
    trim_start_requested = Signal(float)
    trim_end_requested = Signal(float)
    trim_clear_requested = Signal()
    thumbnail_time_requested = Signal(float)

    def __init__(self) -> None:
        super().__init__("媒体预览", description="当前任务 · 输入", density="compact")
        self.setObjectName("mediaPreviewPanel")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumWidth(340)
        self._task_id: str | None = None
        self._input_path: Path | None = None
        self._output_path: Path | None = None
        self._output_available = False
        self._media_info: MediaInfo | None = None
        self._operation = Operation.convert
        self._source = "input"
        self._trim_start: float | None = None
        self._trim_end: float | None = None

        self.source_toggle = SegmentedToggle(
            [
                SegmentOption("input", "输入", "预览任务输入文件"),
                SegmentOption("output", "输出", "预览任务输出文件", enabled=False),
            ]
        )
        layout = self.body_layout()
        self.source_toggle.value_changed.connect(self._on_source_changed)
        layout.addWidget(self._create_source_bar())

        self.player_widget = MediaPlayerWidget()
        layout.addWidget(self.player_widget, 1)

        self.range_summary_label = QLabel("范围：未设置")
        self.range_summary_label.setObjectName("mediaRangeSummaryLabel")
        self.range_summary_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.range_summary_label)

        layout.addWidget(self._create_range_actions())
        layout.addWidget(self._create_thumbnail_actions())
        self.clear()

    def current_task_id(self) -> str | None:
        return self._task_id

    def set_operation(self, operation: Operation) -> None:
        self._operation = operation
        self._sync_actions()

    def set_record(self, record: TaskRecord) -> None:
        previous_task_id = self._task_id
        previous_output_available = self._output_available
        selected_source = self.source_toggle.value() or "input"
        self._task_id = record.task_id
        self._input_path = record.input_path
        self._output_path = record.output_path
        self._media_info = record.media_info if isinstance(record.media_info, MediaInfo) else None
        output_exists = bool(self._output_path and self._output_path.exists())
        self._output_available = output_exists
        should_show_output = (
            output_exists
            and (record.task_id != previous_task_id or not previous_output_available or selected_source == "output")
        )
        if should_show_output:
            self._source = "output"
        else:
            self._source = selected_source
        self._sync_source_toggle()
        self._load_current_source()
        self._sync_actions()

    def clear(self, message: str = "暂无预览") -> None:
        self._task_id = None
        self._input_path = None
        self._output_path = None
        self._output_available = False
        self._media_info = None
        self._source = "input"
        self._trim_start = None
        self._trim_end = None
        self.source_toggle.set_option_enabled("output", False)
        self.source_toggle.set_value("input", emit=False, force=True)
        self.set_description("当前任务 · 输入")
        self.player_widget.clear(message)
        self._sync_range_summary()
        self._sync_actions()

    def set_trim_range(self, start_seconds: float | None, end_seconds: float | None) -> None:
        self._trim_start = start_seconds
        self._trim_end = end_seconds
        self._sync_range_summary()
        self._sync_actions()

    def _create_range_actions(self) -> QWidget:
        action_bar = PanelActionBar(alignment=Qt.AlignmentFlag.AlignLeft)
        self.set_start_button = action_bar.add_button("设为开始", role="quiet")
        self.set_end_button = action_bar.add_button("设为结束", role="quiet")
        self.clear_range_button = action_bar.add_button("清空范围", role="quiet")
        self.set_start_button.clicked.connect(lambda _checked=False: self._emit_trim_start())
        self.set_end_button.clicked.connect(lambda _checked=False: self._emit_trim_end())
        self.clear_range_button.clicked.connect(lambda _checked=False: self.trim_clear_requested.emit())
        return action_bar

    def _create_source_bar(self) -> QWidget:
        row = QWidget()
        row.setObjectName("mediaPreviewSourceBar")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addStretch(1)
        layout.addWidget(self.source_toggle, 0, Qt.AlignmentFlag.AlignRight)
        return row

    def _create_thumbnail_actions(self) -> QWidget:
        row = QWidget()
        row.setObjectName("mediaPreviewActionRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.thumbnail_time_button = QPushButton("设为封面时间")
        self.thumbnail_time_button.setProperty("role", "result")
        self.thumbnail_time_button.setProperty("density", "compact")
        self.thumbnail_time_button.clicked.connect(lambda _checked=False: self._emit_thumbnail_time())
        layout.addWidget(self.thumbnail_time_button)
        layout.addStretch(1)
        return row

    def _on_source_changed(self, value: str) -> None:
        self._source = value
        self._load_current_source()

    def _sync_source_toggle(self) -> None:
        has_output = bool(self._output_path and self._output_path.exists())
        self.source_toggle.set_option_enabled("output", has_output)
        if self._source == "output" and not has_output:
            self._source = "input"
        self.source_toggle.set_value(self._source, emit=False, force=True)

    def _load_current_source(self) -> None:
        source_path = self._current_source_path()
        source_label = "输出" if self._source == "output" else "输入"
        self.set_description(f"当前任务 · {source_label}")
        if source_path is None:
            self.player_widget.clear("暂无输出" if self._source == "output" else "暂无预览")
            return
        duration = self._media_info.duration_seconds if self._media_info else None
        self.player_widget.set_media(
            source_path,
            duration_seconds=duration,
            label=f"{source_label}：{source_path.name}",
            has_video=_preview_has_video(source_path, self._media_info if self._source == "input" else None),
        )

    def _current_source_path(self) -> Path | None:
        if self._source == "output":
            return self._output_path if self._output_path and self._output_path.exists() else None
        return self._input_path if self._input_path and self._input_path.exists() else None

    def _emit_trim_start(self) -> None:
        self.trim_start_requested.emit(self.player_widget.current_seconds())

    def _emit_trim_end(self) -> None:
        self.trim_end_requested.emit(self.player_widget.current_seconds())

    def _emit_thumbnail_time(self) -> None:
        self.thumbnail_time_requested.emit(self.player_widget.current_seconds())

    def _sync_range_summary(self) -> None:
        start = _format_seconds(self._trim_start)
        end = _format_seconds(self._trim_end)
        self.range_summary_label.setText(f"范围：{start} - {end}")

    def _sync_actions(self) -> None:
        has_input = bool(self._input_path and self._input_path.exists())
        trim_supported = has_input and self._operation is not Operation.loop
        self.set_start_button.setEnabled(trim_supported)
        self.set_end_button.setEnabled(trim_supported)
        self.clear_range_button.setEnabled(trim_supported and (self._trim_start is not None or self._trim_end is not None))
        self.thumbnail_time_button.setEnabled(has_input and self._operation is Operation.thumbnail)
        self.thumbnail_time_button.setToolTip(
            "写入封面提取时间点" if self._operation is Operation.thumbnail else "选择“提取封面”动作后可用"
        )


def _format_seconds(value: float | None) -> str:
    if value is None:
        return "--"
    return f"{max(0.0, value):.3f}".rstrip("0").rstrip(".")


def _preview_has_video(path: Path, media_info: MediaInfo | None) -> bool | None:
    if media_info is not None:
        media_has_video = _media_info_has_video(media_info)
        if media_has_video is not None:
            return media_has_video
    if path.suffix.lower() in AUDIO_PREVIEW_EXTENSIONS:
        return False
    return None


def _media_info_has_video(media_info: MediaInfo) -> bool | None:
    streams = media_info.raw.get("streams")
    if not isinstance(streams, list):
        return None
    has_audio = False
    for stream in streams:
        if not isinstance(stream, dict):
            continue
        codec_type = stream.get("codec_type")
        if codec_type == "video":
            return True
        if codec_type == "audio":
            has_audio = True
    if has_audio:
        return False
    return None
