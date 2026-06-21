from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from shared.contracts import MediaInfo, TaskRecord, TaskStatus, operation_category_label, operation_short_label

STATUS_ROLE = int(Qt.ItemDataRole.UserRole) + 1
PROGRESS_ROLE = int(Qt.ItemDataRole.UserRole) + 2
MEDIA_SUMMARY_ROLE = int(Qt.ItemDataRole.UserRole) + 3
ACTION_ENABLED_ROLE = int(Qt.ItemDataRole.UserRole) + 4


class TaskTableModel(QAbstractTableModel):
    HEADERS = ["输入", "输出", "动作", "进度", "操作"]

    def __init__(self) -> None:
        super().__init__()
        self._records: list[TaskRecord] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._records)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid():
            return None
        record = self._records[index.row()]
        column = index.column()
        if role == STATUS_ROLE:
            return record.status
        if role == PROGRESS_ROLE:
            return record.progress
        if role == MEDIA_SUMMARY_ROLE:
            if column == 0:
                return self._input_summary_tags(record)
            if column == 1:
                return self._output_summary_tags(record)
            return []
        if role == ACTION_ENABLED_ROLE:
            return column == 4 and _task_can_be_removed(record)
        if role == Qt.ItemDataRole.TextAlignmentRole and column in {3, 4}:
            return int(Qt.AlignmentFlag.AlignCenter)
        if role not in {Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole}:
            return None
        if role == Qt.ItemDataRole.ToolTipRole:
            return self._tooltip_text(record, column)
        if column == 0:
            return record.input_path.name if role == Qt.ItemDataRole.DisplayRole else str(record.input_path)
        if column == 1:
            if not record.output_path:
                return "待生成" if role == Qt.ItemDataRole.DisplayRole else ""
            return record.output_path.name if role == Qt.ItemDataRole.DisplayRole else str(record.output_path)
        if column == 2:
            return record.operation_text or operation_short_label(record.operation)
        if column == 3:
            return _progress_display_label(record)
        if column == 4:
            return "移除"
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.HEADERS[section]
        return None

    def set_records(self, records: list[TaskRecord]) -> None:
        self.beginResetModel()
        self._records = list(records)
        self.endResetModel()

    def append_record(self, record: TaskRecord) -> None:
        row = len(self._records)
        self.beginInsertRows(QModelIndex(), row, row)
        self._records.append(record)
        self.endInsertRows()

    def notify_record_changed(self, record: TaskRecord) -> None:
        try:
            row = self._records.index(record)
        except ValueError:
            return
        top_left = self.index(row, 0)
        bottom_right = self.index(row, self.columnCount() - 1)
        self.dataChanged.emit(
            top_left,
            bottom_right,
            [
                Qt.ItemDataRole.DisplayRole,
                Qt.ItemDataRole.ToolTipRole,
                Qt.ItemDataRole.TextAlignmentRole,
                STATUS_ROLE,
                PROGRESS_ROLE,
                MEDIA_SUMMARY_ROLE,
                ACTION_ENABLED_ROLE,
            ],
        )

    def records(self) -> list[TaskRecord]:
        return list(self._records)

    def remove_records(self, task_ids: set[str]) -> int:
        if not task_ids:
            return 0
        rows_to_remove = [index for index, record in enumerate(self._records) if record.task_id in task_ids]
        if not rows_to_remove:
            return 0
        for row in reversed(rows_to_remove):
            self.beginRemoveRows(QModelIndex(), row, row)
            self._records.pop(row)
            self.endRemoveRows()
        return len(rows_to_remove)

    def _input_summary_tags(self, record: TaskRecord) -> list[str]:
        tags: list[str] = []
        extension = record.input_path.suffix.lstrip(".").upper()
        if extension:
            tags.append(extension)

        size = self._file_size(record.input_path)
        if size is not None:
            tags.append(_format_bytes(size))

        media_info = record.media_info if isinstance(record.media_info, MediaInfo) else None
        if media_info and media_info.has_error:
            tags.append("读取失败")
            return tags
        if record.status is TaskStatus.probing:
            tags.append("读取中")

        if media_info:
            tags.extend(_media_info_tags(media_info))
        return tags or ["等待读取"]

    def _output_summary_tags(self, record: TaskRecord) -> list[str]:
        if not record.output_path:
            return ["待生成"]
        tags: list[str] = []
        extension = record.output_path.suffix.lstrip(".").upper()
        if extension:
            tags.append(extension)
        size = self._file_size(record.output_path)
        if size is not None:
            tags.append(_format_bytes(size))
        return tags or ["待生成"]

    def _file_size(self, path: Path) -> int | None:
        try:
            return path.stat().st_size
        except OSError:
            return None

    def _tooltip_text(self, record: TaskRecord, column: int) -> str:
        if column == 0:
            tags = " · ".join(self._input_summary_tags(record))
            media_info = record.media_info if isinstance(record.media_info, MediaInfo) else None
            if media_info and media_info.has_error and media_info.error_message:
                return f"输入文件：{record.input_path.name}\n路径：{record.input_path}\n媒体摘要：{tags}\n读取失败：{media_info.error_message}"
            return f"输入文件：{record.input_path.name}\n路径：{record.input_path}\n媒体摘要：{tags}"
        if column == 1:
            tags = " · ".join(self._output_summary_tags(record))
            if not record.output_path:
                return f"输出：待生成\n摘要：{tags}"
            return f"输出文件：{record.output_path.name}\n路径：{record.output_path}\n摘要：{tags}"
        if column == 2:
            operation = record.operation_text or operation_short_label(record.operation)
            category = operation_category_label(record.operation)
            if record.operation_text:
                return f"动作：{operation}\n首个动作：{operation_short_label(record.operation)}\n分类：{category}"
            return f"动作：{operation}\n分类：{category}"
        if column == 3:
            tooltip = f"状态：{_status_label(record.status)}\n进度：{_progress_display_label(record)}"
            if record.message:
                return f"{tooltip}\n消息：{record.message}"
            return tooltip
        if column == 4:
            if _task_can_be_removed(record):
                return "从任务队列移除此任务"
            return "运行中或读取中的任务不可移除，请先取消"
        return ""


def _media_info_tags(media_info: MediaInfo) -> list[str]:
    raw = media_info.raw
    format_info = raw.get("format", {}) if isinstance(raw.get("format"), dict) else {}
    streams = raw.get("streams", []) if isinstance(raw.get("streams"), list) else []
    video_stream = _first_stream(streams, "video")
    audio_stream = _first_stream(streams, "audio")

    tags: list[str] = []
    duration = media_info.duration_seconds or _float_value(format_info.get("duration"))
    if duration:
        tags.append(_format_duration(duration))

    if video_stream:
        height = _int_value(video_stream.get("height"))
        if height:
            tags.append(_format_resolution(height))
        video_codec = _codec_label(video_stream.get("codec_name"))
        if video_codec:
            tags.append(video_codec)

    if audio_stream:
        audio_codec = _codec_label(audio_stream.get("codec_name"))
        if audio_codec:
            tags.append(audio_codec)
    return tags


def _first_stream(streams: list[Any], codec_type: str) -> dict[str, Any]:
    for stream in streams:
        if isinstance(stream, dict) and stream.get("codec_type") == codec_type:
            return stream
    return {}


def _float_value(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _int_value(value: object) -> int | None:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _format_duration(duration_seconds: float) -> str:
    total = int(round(duration_seconds))
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def _format_resolution(height: int) -> str:
    if height >= 2160:
        return "4K"
    if height >= 1440:
        return "1440p"
    if height >= 1080:
        return "1080p"
    if height >= 720:
        return "720p"
    return f"{height}p"


def _progress_display_label(record: TaskRecord) -> str:
    if record.status is TaskStatus.probing:
        return "读取中"
    if record.status is TaskStatus.ready:
        return "就绪"
    if record.status is TaskStatus.pending:
        return "待处理"
    if record.status is TaskStatus.running:
        if record.progress is None:
            return "运行中"
        return f"{int(max(0.0, min(record.progress, 1.0)) * 100)}%"
    if record.status is TaskStatus.succeeded:
        return "完成"
    if record.status is TaskStatus.failed:
        return "失败"
    if record.status is TaskStatus.cancelled:
        return "取消"
    return _status_label(record.status)


def _task_can_be_removed(record: TaskRecord) -> bool:
    return record.status not in {TaskStatus.probing, TaskStatus.running}


def _codec_label(value: object) -> str:
    codec = str(value or "").strip().lower()
    return {
        "h264": "H.264",
        "hevc": "HEVC",
        "h265": "HEVC",
        "av1": "AV1",
        "vp9": "VP9",
        "vp8": "VP8",
        "aac": "AAC",
        "mp3": "MP3",
        "opus": "Opus",
        "flac": "FLAC",
        "pcm_s16le": "PCM",
    }.get(codec, codec.upper())


def _format_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{size} B"


def _status_label(status: TaskStatus) -> str:
    return {
        TaskStatus.probing: "读取中",
        TaskStatus.ready: "就绪",
        TaskStatus.pending: "待处理",
        TaskStatus.running: "运行中",
        TaskStatus.succeeded: "完成",
        TaskStatus.failed: "失败",
        TaskStatus.cancelled: "取消",
    }.get(status, status.value)
