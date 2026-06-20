from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt

from desktop.app.ui.widgets.task_table_model import ACTION_ENABLED_ROLE, MEDIA_SUMMARY_ROLE, TaskTableModel
from shared.contracts import MediaInfo, Operation, TaskRecord, TaskStatus


def test_task_table_columns_match_queue_design() -> None:
    assert TaskTableModel.HEADERS == ["输入", "输出", "行为", "进度", "操作"]


def test_task_table_operation_column_uses_short_action_label() -> None:
    record = TaskRecord(operation=Operation.convert, input_path=Path("clip.mov"), status=TaskStatus.ready)
    model = TaskTableModel()
    model.append_record(record)

    index = model.index(0, 2)

    assert model.data(index, Qt.ItemDataRole.DisplayRole) == "转换格式"
    tooltip = str(model.data(index, Qt.ItemDataRole.ToolTipRole))
    assert "行为：转换格式" in tooltip
    assert "分类：基础" in tooltip


def test_task_table_remove_action_enabled_by_task_status() -> None:
    ready_record = TaskRecord(operation=Operation.convert, input_path=Path("ready.mov"), status=TaskStatus.ready)
    running_record = TaskRecord(operation=Operation.convert, input_path=Path("running.mov"), status=TaskStatus.running)
    model = TaskTableModel()
    model.append_record(ready_record)
    model.append_record(running_record)

    assert model.data(model.index(0, 4), Qt.ItemDataRole.DisplayRole) == "移除"
    assert model.data(model.index(0, 4), ACTION_ENABLED_ROLE) is True
    assert model.data(model.index(1, 4), ACTION_ENABLED_ROLE) is False


def test_task_table_progress_column_carries_status_labels() -> None:
    ready_record = TaskRecord(operation=Operation.convert, input_path=Path("ready.mov"), status=TaskStatus.ready)
    running_record = TaskRecord(
        operation=Operation.convert,
        input_path=Path("running.mov"),
        status=TaskStatus.running,
        progress=0.42,
    )
    failed_record = TaskRecord(operation=Operation.convert, input_path=Path("failed.mov"), status=TaskStatus.failed)
    model = TaskTableModel()
    model.append_record(ready_record)
    model.append_record(running_record)
    model.append_record(failed_record)

    assert model.data(model.index(0, 3), Qt.ItemDataRole.DisplayRole) == "就绪"
    assert model.data(model.index(1, 3), Qt.ItemDataRole.DisplayRole) == "42%"
    assert model.data(model.index(2, 3), Qt.ItemDataRole.DisplayRole) == "失败"


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

    index = model.index(0, 0)
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

    index = model.index(0, 1)

    assert model.data(index, MEDIA_SUMMARY_ROLE) == ["MP4", "4.0 KB"]
    assert model.data(index, Qt.ItemDataRole.DisplayRole) == "clip.mp4"


def test_task_table_tooltips_show_full_paths_and_status_message(tmp_path: Path) -> None:
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

    assert str(input_path) in str(model.data(model.index(0, 0), Qt.ItemDataRole.ToolTipRole))
    assert str(output_path) in str(model.data(model.index(0, 1), Qt.ItemDataRole.ToolTipRole))
    status_tooltip = str(model.data(model.index(0, 3), Qt.ItemDataRole.ToolTipRole))
    assert record.message in status_tooltip


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

    tooltip = str(model.data(model.index(0, 0), Qt.ItemDataRole.ToolTipRole))

    assert "读取失败" in tooltip
    assert "ffprobe could not read this file" in tooltip
