from __future__ import annotations

from pathlib import Path

from desktop.app.services.output_service import BatchZipResult, OutputService
from desktop.app.tasks.zip_results_worker import ZipResultsWorker
from shared.contracts import Operation, TaskRecord, TaskStatus


def test_zip_results_worker_emits_result(tmp_path: Path) -> None:
    output_path = tmp_path / "out.mp4"
    output_path.write_bytes(b"ok")
    record = TaskRecord(
        operation=Operation.convert,
        input_path=tmp_path / "input.mp4",
        output_path=output_path,
        status=TaskStatus.succeeded,
    )
    worker = ZipResultsWorker(OutputService(), [record], tmp_path)
    results: list[BatchZipResult] = []
    errors: list[str] = []
    finished: list[bool] = []
    worker.result_ready.connect(results.append)
    worker.error_occurred.connect(errors.append)
    worker.finished.connect(lambda: finished.append(True))

    worker.run()

    assert errors == []
    assert finished == [True]
    assert len(results) == 1
    assert results[0].packed_count == 1
    assert results[0].archive_path is not None
    assert results[0].archive_path.exists()


def test_zip_results_worker_reports_cancelled(tmp_path: Path) -> None:
    output_path = tmp_path / "out.mp4"
    output_path.write_bytes(b"ok")
    record = TaskRecord(
        operation=Operation.convert,
        input_path=tmp_path / "input.mp4",
        output_path=output_path,
        status=TaskStatus.succeeded,
    )
    worker = ZipResultsWorker(OutputService(), [record], tmp_path)
    results: list[BatchZipResult] = []
    errors: list[str] = []
    worker.result_ready.connect(results.append)
    worker.error_occurred.connect(errors.append)

    worker.cancel()
    worker.run()

    assert results == []
    assert errors == ["打包已取消"]
    assert not list(tmp_path.glob("ffmpeg-gui-batch-*.zip"))
