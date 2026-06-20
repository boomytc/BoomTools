from __future__ import annotations

from pathlib import Path

from desktop.app.controllers.main_controller import MainController
from desktop.app.runtime.binaries import RuntimeHealth
from shared.contracts import AppConfig, Operation


class _Signal:
    def connect(self, *_: object, **__: object) -> None:
        return None


class _FakeWindow:
    def __init__(self) -> None:
        self._operation_payload = (Operation.convert, {}, {})
        self._selected_input_path: Path | None = None
        self._selected_output_dir = "/tmp"
        self._ffmpeg_bin = "ffmpeg"
        self._ffprobe_bin = "ffprobe"
        self.stack_mode_enabled = False
        self.error_messages: list[str] = []
        self.status_messages: list[str] = []

        self.input_file_selected = _Signal()
        self.batch_files_selected = _Signal()
        self.output_dir_selected = _Signal()
        self.refresh_requested = _Signal()
        self.start_requested = _Signal()
        self.cancel_requested = _Signal()
        self.cancel_queue_requested = _Signal()
        self.remove_pending_requested = _Signal()
        self.stack_mode_toggled = _Signal()
        self.stack_add_requested = _Signal()
        self.stack_move_up_requested = _Signal()
        self.stack_move_down_requested = _Signal()
        self.stack_remove_requested = _Signal()
        self.stack_clear_requested = _Signal()
        self.command_preview_requested = _Signal()
        self.open_output_requested = _Signal()
        self.open_output_dir_requested = _Signal()
        self.copy_output_path_requested = _Signal()
        self.closing = _Signal()

        self._stack_items: list[str] = []

    def selected_operation_payload(self):
        return self._operation_payload

    def set_operation_payload(self, operation, options: dict[str, object], extra_inputs: dict[str, Path]) -> None:
        self._operation_payload = (operation, options, extra_inputs)

    def set_input_path(self, path: Path | None) -> None:
        self._selected_input_path = path

    def selected_input_path(self) -> Path | None:
        return self._selected_input_path

    def selected_output_dir(self) -> str:
        return self._selected_output_dir

    def selected_ffmpeg_bin(self) -> str:
        return self._ffmpeg_bin

    def selected_ffprobe_bin(self) -> str:
        return self._ffprobe_bin

    def stack_mode(self) -> bool:
        return self.stack_mode_enabled

    def set_start_enabled(self, _enabled: bool) -> None:
        return None

    def show_error(self, message: str) -> None:
        self.error_messages.append(message)

    def show_status(self, message: str) -> None:
        self.status_messages.append(message)

    def set_stack_items(self, items: list[str]) -> None:
        self._stack_items = items

    def set_batch_progress(self, *_: object) -> None:
        return None

    def set_busy(self, *_: object) -> None:
        return None

    def set_current_output(self, _path: Path | None) -> None:
        return None

    def set_command_preview(self, _command: str) -> None:
        return None

    def set_output_estimate(self, _estimate: str) -> None:
        return None

    def clear_log(self) -> None:
        return None

    def append_log(self, _line: str) -> None:
        return None

    def set_batch_buttons(self, *_: object) -> None:
        return None

    def set_stack_mode(self, *_: object) -> None:
        return None

    def _update_stack_add_enabled(self) -> None:
        return None

class _ConfigService:
    def load(self) -> AppConfig:
        return AppConfig(ffmpeg_bin="ffmpeg", ffprobe_bin="ffprobe", output_dir=Path("/tmp"))

    def save(self, _config: AppConfig) -> None:
        return None


class _FfmpegService:
    def __init__(self, health: RuntimeHealth) -> None:
        self._health = health

    def check_health(self, *_: str) -> RuntimeHealth:
        return self._health


class _OutputService:
    def normalize_output_dir(self, path: Path | str) -> Path:
        return Path(path)

    def default_output_dir(self) -> Path:
        return Path("/tmp")


class _LogService:
    def save_task_log(self, *_: object, **__: object) -> None:
        return None


class _TaskModel:
    def append_record(self, _record: object) -> None:
        return None

    def notify_record_changed(self, _record: object) -> None:
        return None

    def remove_records(self, _record_ids: set[str]) -> None:
        return None


class _TaskManager:
    def clear_batch_cancel_flag(self) -> None:
        return None

    def request_cancel_batch(self) -> None:
        return None

    def batch_cancel_requested(self) -> bool:
        return False

    def clear_current(self, *_: object) -> None:
        return None

    def create_worker(self, *_: object, **__: object) -> object:
        raise AssertionError("should not reach worker creation")


def _make_controller(window: _FakeWindow) -> MainController:
    return MainController(
        window=window,
        task_model=_TaskModel(),
        config_service=_ConfigService(),
        ffmpeg_service=_FfmpegService(
            RuntimeHealth(
                ok=True,
                ffmpeg_available=True,
                ffprobe_available=True,
                ffmpeg_path="ffmpeg",
                ffprobe_path="ffprobe",
            )
        ),
        output_service=_OutputService(),
        log_service=_LogService(),
        task_manager=_TaskManager(),
    )


def test_start_task_catches_subtitle_missing_input_error(tmp_path: Path) -> None:
    window = _FakeWindow()
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"\x00")
    window.set_operation_payload(Operation.subtitles, {"mode": "soft"}, {})
    window.set_input_path(input_path)

    controller = _make_controller(window)
    controller.start_task()

    assert any("请选择字幕文件" in message for message in window.error_messages)


def test_stack_add_catches_subtitle_missing_input_error(tmp_path: Path) -> None:
    window = _FakeWindow()
    window.set_operation_payload(Operation.subtitles, {"mode": "soft"}, {})
    controller = _make_controller(window)

    controller._on_stack_add_requested()

    assert any("请选择字幕文件" in message for message in window.error_messages)
    assert controller._stack_items == []
