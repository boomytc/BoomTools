from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt

from desktop.app.ui.widgets.task_table_model import MEDIA_SUMMARY_ROLE, TaskTableModel
from shared.contracts import MediaInfo, Operation, TaskRecord, TaskStatus


def test_task_table_columns_match_queue_design() -> None:
    assert TaskTableModel.HEADERS == ["状态", "输入媒体", "操作", "输出", "进度", "消息"]


def test_task_table_media_summary_uses_tags(tmp_path: Path) -> None:
    input_path = tmp_path / "clip.mp4"
    input_path.write_bytes(b"0" * 2048)
    record = TaskRecord(
        operation=Operation.convert,
        input_path=input_path,
        status=TaskStatus.ready,
        media_info=MediaInfo(
            raw={
                "streams": [
                    {"codec_type": "video", "height": 1080, "codec_name": "h264"},
                    {"codec_type": "audio", "codec_name": "aac"},
                ],
                "format": {"duration": "100.0"},
            },
            duration_seconds=100.0,
        ),
    )
    model = TaskTableModel()
    model.append_record(record)

    index = model.index(0, 1)
    tags = model.data(index, MEDIA_SUMMARY_ROLE)

    assert tags == ["MP4", "2.0 KB", "1:40", "1080p", "H.264", "AAC"]
    assert model.data(index, Qt.ItemDataRole.DisplayRole) == "clip.mp4"


def test_task_table_output_summary_uses_actual_output_file_size(tmp_path: Path) -> None:
    input_path = tmp_path / "clip.mov"
    output_path = tmp_path / "clip.mp4"
    input_path.write_bytes(b"0")
    output_path.write_bytes(b"0" * 4096)
    record = TaskRecord(
        operation=Operation.convert,
        input_path=input_path,
        output_path=output_path,
        status=TaskStatus.succeeded,
    )
    model = TaskTableModel()
    model.append_record(record)

    index = model.index(0, 3)

    assert model.data(index, MEDIA_SUMMARY_ROLE) == ["MP4", "4.0 KB"]
    assert model.data(index, Qt.ItemDataRole.DisplayRole) == "clip.mp4"


def test_task_table_tooltips_show_full_paths_and_messages(tmp_path: Path) -> None:
    input_path = tmp_path / "a very long input filename that will be elided.mov"
    output_path = tmp_path / "a very long output filename that will be elided.mp4"
    input_path.write_bytes(b"0")
    record = TaskRecord(
        operation=Operation.convert,
        input_path=input_path,
        output_path=output_path,
        status=TaskStatus.failed,
        message="A long ffmpeg error message that should be visible in the tooltip.",
    )
    model = TaskTableModel()
    model.append_record(record)

    assert str(input_path) in str(model.data(model.index(0, 1), Qt.ItemDataRole.ToolTipRole))
    assert str(output_path) in str(model.data(model.index(0, 3), Qt.ItemDataRole.ToolTipRole))
    assert model.data(model.index(0, 5), Qt.ItemDataRole.ToolTipRole) == record.message


def test_task_table_media_summary_tooltip_shows_probe_error(tmp_path: Path) -> None:
    input_path = tmp_path / "broken.mp4"
    input_path.write_bytes(b"0")
    record = TaskRecord(
        operation=Operation.convert,
        input_path=input_path,
        status=TaskStatus.ready,
        media_info=MediaInfo(raw={"error": "ffprobe could not read this file"}, duration_seconds=None),
    )
    model = TaskTableModel()
    model.append_record(record)

    tooltip = str(model.data(model.index(0, 1), Qt.ItemDataRole.ToolTipRole))

    assert "读取失败" in tooltip
    assert "ffprobe could not read this file" in tooltip
