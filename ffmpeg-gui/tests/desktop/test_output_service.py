from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zipfile import ZipFile

from desktop.app.services.output_service import OutputService
from shared.contracts import Operation, TaskRecord, TaskStatus


def test_zip_successful_outputs_handles_unicode_spaces_and_duplicate_names(tmp_path: Path) -> None:
    first_dir = tmp_path / "中文 目录"
    second_dir = tmp_path / "other dir"
    first_dir.mkdir()
    second_dir.mkdir()
    first_output = first_dir / "结果 文件.mp4"
    second_output = second_dir / "结果 文件.mp4"
    failed_output = tmp_path / "failed.mp4"
    first_output.write_bytes(b"first")
    second_output.write_bytes(b"second")
    failed_output.write_bytes(b"failed")
    missing_output = tmp_path / "missing.mp4"
    zip_dir = tmp_path / "zip 输出"

    records = [
        TaskRecord(
            operation=Operation.convert,
            input_path=tmp_path / "in 1.mp4",
            output_path=first_output,
            status=TaskStatus.succeeded,
        ),
        TaskRecord(
            operation=Operation.convert,
            input_path=tmp_path / "in 2.mp4",
            output_path=second_output,
            status=TaskStatus.succeeded,
        ),
        TaskRecord(
            operation=Operation.convert,
            input_path=tmp_path / "in 3.mp4",
            output_path=failed_output,
            status=TaskStatus.failed,
        ),
        TaskRecord(
            operation=Operation.convert,
            input_path=tmp_path / "in 4.mp4",
            output_path=missing_output,
            status=TaskStatus.succeeded,
        ),
        TaskRecord(
            operation=Operation.convert,
            input_path=tmp_path / "in 5.mp4",
            output_path=None,
            status=TaskStatus.cancelled,
        ),
    ]

    result = OutputService().zip_successful_outputs(
        records,
        zip_dir,
        timestamp=datetime(2026, 6, 21, 10, 11, 12),
    )

    assert result.archive_path == zip_dir / "ffmpeg-gui-batch-20260621-101112.zip"
    assert result.packed_count == 2
    assert result.skipped_count == 3
    assert result.archive_path.exists()
    with ZipFile(result.archive_path) as archive:
        assert archive.namelist() == ["结果 文件.mp4", "结果 文件-2.mp4"]
        assert archive.read("结果 文件.mp4") == b"first"
        assert archive.read("结果 文件-2.mp4") == b"second"


def test_zip_successful_outputs_returns_empty_result_without_archive(tmp_path: Path) -> None:
    records = [
        TaskRecord(
            operation=Operation.convert,
            input_path=tmp_path / "failed.mp4",
            output_path=None,
            status=TaskStatus.failed,
        ),
        TaskRecord(
            operation=Operation.convert,
            input_path=tmp_path / "cancelled.mp4",
            output_path=tmp_path / "missing.mp4",
            status=TaskStatus.cancelled,
        ),
    ]

    result = OutputService().zip_successful_outputs(
        records,
        tmp_path,
        timestamp=datetime(2026, 6, 21, 10, 11, 12),
    )

    assert result.archive_path is None
    assert result.packed_count == 0
    assert result.skipped_count == 2
    assert not (tmp_path / "ffmpeg-gui-batch-20260621-101112.zip").exists()


def test_zip_successful_outputs_uses_unique_archive_name(tmp_path: Path) -> None:
    output_path = tmp_path / "out.mp4"
    output_path.write_bytes(b"ok")
    existing_archive = tmp_path / "ffmpeg-gui-batch-20260621-101112.zip"
    existing_archive.write_bytes(b"existing")
    record = TaskRecord(
        operation=Operation.convert,
        input_path=tmp_path / "input.mp4",
        output_path=output_path,
        status=TaskStatus.succeeded,
    )

    result = OutputService().zip_successful_outputs(
        [record],
        tmp_path,
        timestamp=datetime(2026, 6, 21, 10, 11, 12),
    )

    assert result.archive_path == tmp_path / "ffmpeg-gui-batch-20260621-101112-2.zip"
    assert result.archive_path.exists()
