from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from desktop.app.runtime.binaries import RuntimeHealth
from desktop.app.runtime.ffmpeg import parse_progress_line
from desktop.app.viewmodels.app_state import AppState
from shared.contracts import TaskRecord, TaskStatus
from shared.contracts.operations import Operation


def test_parse_progress_line_with_duration() -> None:
    assert parse_progress_line("out_time_us=1000000", 2.0) == 0.5
    assert parse_progress_line("out_time=00:00:01.000000", 2.0) == 0.5
    assert parse_progress_line("speed=1x", 2.0) is None


def test_parse_progress_line_without_duration_is_indeterminate() -> None:
    assert parse_progress_line("out_time_us=1000000", None) is None


def test_app_state_start_gating() -> None:
    with TemporaryDirectory() as tmp:
        input_path = Path(tmp) / "中文 file.mp4"
        input_path.write_bytes(b"placeholder")
        state = AppState(
            input_path=input_path,
            runtime_health=RuntimeHealth(
                ok=True,
                ffmpeg_available=True,
                ffprobe_available=True,
                ffmpeg_path="ffmpeg",
                ffprobe_path="ffprobe",
            ),
        )
        assert state.can_start()

        state.current_task = TaskRecord(operation=Operation.convert, input_path=input_path, status=TaskStatus.running)
        assert not state.can_start()
