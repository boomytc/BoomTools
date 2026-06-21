from __future__ import annotations

from pathlib import Path

from desktop.app.controllers.main_controller import MainController
from desktop.app.core.config import AppConfig
from desktop.app.runtime.binaries import RuntimeHealth
from desktop.app.runtime.ffmpeg import CommandSpec
from shared.contracts import Operation, TaskStatus


class _Signal:
    def connect(self, *_: object, **__: object) -> None:
        return None


class _FakeWindow:
    def __init__(self) -> None:
        self._operation_payload = (Operation.convert, {}, {})
        self._selected_input_path: Path | None = None
        self._selected_batch_paths: list[Path] = []
        self._selected_output_dir = "/tmp"
        self._ffmpeg_bin = "ffmpeg"
        self._ffprobe_bin = "ffprobe"
        self.stack_mode_enabled = False
        self.batch_input_mode_enabled = False
        self.error_messages: list[str] = []
        self.status_messages: list[str] = []

        self.input_file_selected = _Signal()
        self.input_mode_changed = _Signal()
        self.batch_files_selected = _Signal()
        self.batch_files_cleared = _Signal()
        self.output_dir_selected = _Signal()
        self.refresh_requested = _Signal()
        self.start_requested = _Signal()
        self.cancel_requested = _Signal()
        self.cancel_queue_requested = _Signal()
        self.remove_pending_requested = _Signal()
        self.task_remove_requested = _Signal()
        self.stack_mode_toggled = _Signal()
        self.stack_add_requested = _Signal()
        self.stack_remove_requested = _Signal()
        self.stack_clear_requested = _Signal()
        self.stack_item_selected = _Signal()
        self.stack_item_moved = _Signal()
        self.command_preview_requested = _Signal()
        self.open_output_requested = _Signal()
        self.open_output_dir_requested = _Signal()
        self.copy_output_path_requested = _Signal()
        self.closing = _Signal()

        self._stack_items: list[str] = []

    def selected_operation_payload(self):
        return self._operation_payload

    def selected_operation(self) -> Operation:
        return self._operation_payload[0]

    def set_operation_payload(self, operation, options: dict[str, object], extra_inputs: dict[str, Path]) -> None:
        self._operation_payload = (operation, options, extra_inputs)

    def set_input_path(self, path: Path | None) -> None:
        self._selected_input_path = path

    def selected_input_path(self) -> Path | None:
        return self._selected_input_path

    def selected_batch_paths(self) -> list[Path]:
        return list(self._selected_batch_paths)

    def set_batch_paths(self, paths: list[Path]) -> None:
        self._selected_batch_paths = list(paths)

    def batch_input_mode(self) -> bool:
        return self.batch_input_mode_enabled

    def set_batch_input_mode(self, enabled: bool) -> None:
        self.batch_input_mode_enabled = enabled

    def set_batch_input_paths(self, paths: list[Path]) -> None:
        self._selected_batch_paths = list(paths)

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

    def set_runtime_health(self, _health: RuntimeHealth) -> None:
        return None

    def set_media_info(self, _media_info: object) -> None:
        return None

    def show_error(self, message: str) -> None:
        self.error_messages.append(message)

    def show_status(self, message: str) -> None:
        self.status_messages.append(message)

    def set_stack_items(self, items: list[str]) -> None:
        self._stack_items = items

    def set_batch_progress(self, *_: object) -> None:
        return None

    def reset_progress(self) -> None:
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

    def refresh_stack_controls(self) -> None:
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

    def build_command(self, *_: object, **__: object) -> CommandSpec:
        return CommandSpec(args=["ffmpeg", "-i", "input_placeholder", "out.mp4"], output_path=Path("/tmp/out.mp4"), output_name="out.mp4")


class _OutputService:
    def normalize_output_dir(self, path: Path | str) -> Path:
        return Path(path)

    def default_output_dir(self) -> Path:
        return Path("/tmp")


class _LogService:
    def save_task_log(self, *_: object, **__: object) -> None:
        return None


class _TaskModel:
    def __init__(self) -> None:
        self._records: list[object] = []

    def append_record(self, record: object) -> None:
        self._records.append(record)

    def notify_record_changed(self, _record: object) -> None:
        return None

    def remove_records(self, record_ids: set[str]) -> None:
        self._records = [record for record in self._records if getattr(record, "task_id", "") not in record_ids]
        return None

    def records(self) -> list[object]:
        return list(self._records)


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


def _make_controller(window: _FakeWindow, task_model: _TaskModel | None = None) -> MainController:
    return MainController(
        window=window,
        task_model=task_model or _TaskModel(),
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


def test_stack_add_reports_unsupported_subtitle_operation(tmp_path: Path) -> None:
    window = _FakeWindow()
    window.set_operation_payload(Operation.subtitles, {"mode": "soft"}, {})
    controller = _make_controller(window)

    controller._on_stack_add_requested()

    assert any("当前操作不支持加入 Stack" in message for message in window.error_messages)
    assert controller._stack_items == []


def test_stack_item_selection_syncs_operation_payload() -> None:
    window = _FakeWindow()
    window.stack_mode_enabled = True
    controller = _make_controller(window)
    window.set_operation_payload(Operation.rotate, {"mode": "cw90", "output_format": "mp4"}, {})
    controller._on_stack_add_requested()
    window.set_operation_payload(
        Operation.crop,
        {"x": 4, "y": 8, "width": 320, "height": 180, "output_format": "mp4"},
        {},
    )
    controller._on_stack_add_requested()
    window.set_operation_payload(Operation.adjust, {"brightness": 0.2, "contrast": 1.0, "saturation": 1.1}, {})
    controller._on_stack_item_selected(0)

    operation, options, extra_inputs = window.selected_operation_payload()
    assert operation is Operation.rotate
    assert options == {"mode": "cw90", "output_format": "mp4"}
    assert extra_inputs == {}


def test_stack_item_selection_keeps_repeated_operation_payloads_by_index() -> None:
    window = _FakeWindow()
    window.stack_mode_enabled = True
    controller = _make_controller(window)

    first_crop = {"x": 0, "y": 0, "width": 320, "height": 180, "output_format": "mp4"}
    second_crop = {"x": 40, "y": 24, "width": 640, "height": 360, "output_format": "mp4"}

    window.set_operation_payload(Operation.crop, first_crop, {})
    controller._on_stack_add_requested()
    window.set_operation_payload(Operation.crop, second_crop, {})
    controller._on_stack_add_requested()

    controller._on_stack_item_selected(0)
    operation, options, extra_inputs = window.selected_operation_payload()
    assert operation is Operation.crop
    assert options == first_crop
    assert extra_inputs == {}

    controller._on_stack_item_selected(1)
    operation, options, extra_inputs = window.selected_operation_payload()
    assert operation is Operation.crop
    assert options == second_crop
    assert extra_inputs == {}


def test_stack_add_syncs_parameter_payload_to_stored_follow_up_step() -> None:
    window = _FakeWindow()
    window.stack_mode_enabled = True
    controller = _make_controller(window)

    window.set_operation_payload(
        Operation.crop,
        {"start_seconds": 1.0, "x": 0, "y": 0, "width": 320, "height": 180, "output_format": "mp4"},
        {},
    )
    controller._on_stack_add_requested()

    window.set_operation_payload(
        Operation.crop,
        {"start_seconds": 2.0, "x": 10, "y": 20, "width": 640, "height": 360, "output_format": "mp4"},
        {},
    )
    controller._on_stack_add_requested()

    operation, options, extra_inputs = window.selected_operation_payload()
    assert operation is Operation.crop
    assert options == {"x": 10, "y": 20, "width": 640, "height": 360, "output_format": "mp4"}
    assert extra_inputs == {}
    assert controller._stack_items[0][1]["start_seconds"] == 1.0
    assert "start_seconds" not in controller._stack_items[1][1]


def test_stack_item_move_reorders_payloads_by_index() -> None:
    window = _FakeWindow()
    window.stack_mode_enabled = True
    controller = _make_controller(window)

    first_crop = {"x": 0, "y": 0, "width": 320, "height": 180, "output_format": "mp4"}
    second_crop = {"x": 40, "y": 24, "width": 640, "height": 360, "output_format": "mp4"}
    third_crop = {"x": 80, "y": 48, "width": 960, "height": 540, "output_format": "mp4"}

    window.set_operation_payload(Operation.crop, first_crop, {})
    controller._on_stack_add_requested()
    window.set_operation_payload(Operation.crop, second_crop, {})
    controller._on_stack_add_requested()
    window.set_operation_payload(Operation.crop, third_crop, {})
    controller._on_stack_add_requested()

    controller._on_stack_item_moved(0, 2)

    assert [item[1] for item in controller._stack_items] == [second_crop, third_crop, first_crop]
    operation, options, extra_inputs = window.selected_operation_payload()
    assert operation is Operation.crop
    assert options == first_crop
    assert extra_inputs == {}


def test_collect_input_paths_respects_single_input_mode(tmp_path: Path) -> None:
    window = _FakeWindow()
    single_path = tmp_path / "single.mp4"
    batch_path = tmp_path / "batch.mp4"
    single_path.write_bytes(b"\x00")
    batch_path.write_bytes(b"\x00")
    window.set_input_path(single_path)
    window.set_batch_paths([batch_path])

    controller = _make_controller(window)
    controller.state.input_mode = "single"
    controller.state.batch_input_paths = [batch_path]

    assert controller._collect_input_paths() == [single_path]


def test_multiple_files_reject_unsupported_operation(tmp_path: Path) -> None:
    window = _FakeWindow()
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    first.write_bytes(b"\x00")
    second.write_bytes(b"\x00")
    window.set_operation_payload(Operation.thumbnail, {"timestamp_seconds": 0.0, "image_format": "jpg"}, {})
    window.set_batch_paths([first, second])

    controller = _make_controller(window)
    controller.state.runtime_health = RuntimeHealth(
        ok=True,
        ffmpeg_available=True,
        ffprobe_available=True,
        ffmpeg_path="ffmpeg",
        ffprobe_path="ffprobe",
    )
    controller.state.input_mode = "batch"
    controller.state.batch_input_paths = [first, second]
    controller.state.input_path = first
    window.set_batch_input_mode(True)
    controller.start_task()

    assert any("该操作不支持批处理" in message for message in window.error_messages)


def test_batch_selection_creates_ready_queue_rows(tmp_path: Path) -> None:
    window = _FakeWindow()
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mov"
    first.write_bytes(b"\x00")
    second.write_bytes(b"\x00")
    task_model = _TaskModel()

    controller = _make_controller(window, task_model=task_model)
    controller.on_batch_files_selected([str(first), str(second)])

    assert [record.input_path for record in task_model.records()] == [first, second]
    assert [record.status for record in task_model.records()] == [TaskStatus.ready, TaskStatus.ready]


def test_file_selection_appends_to_existing_queue_rows(tmp_path: Path) -> None:
    window = _FakeWindow()
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mov"
    third = tmp_path / "third.webm"
    for path in (first, second, third):
        path.write_bytes(b"\x00")
    task_model = _TaskModel()

    controller = _make_controller(window, task_model=task_model)
    controller.on_batch_files_selected([str(first), str(second)])
    controller.on_batch_files_selected([str(third)])

    assert [record.input_path for record in task_model.records()] == [first, second, third]


def test_remove_task_removes_single_prepared_queue_row(tmp_path: Path) -> None:
    window = _FakeWindow()
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mov"
    first.write_bytes(b"\x00")
    second.write_bytes(b"\x00")
    task_model = _TaskModel()

    controller = _make_controller(window, task_model=task_model)
    controller.on_batch_files_selected([str(first), str(second)])
    task_id = task_model.records()[0].task_id
    controller.remove_task(task_id)

    assert [record.input_path for record in task_model.records()] == [second]
    assert controller._prepared_input_paths() == [second]
    assert window.selected_batch_paths() == [second]


def test_remove_task_rejects_running_task(tmp_path: Path) -> None:
    window = _FakeWindow()
    first = tmp_path / "running.mp4"
    second = tmp_path / "queued.mp4"
    first.write_bytes(b"\x00")
    second.write_bytes(b"\x00")
    task_model = _TaskModel()

    controller = _make_controller(window, task_model=task_model)
    controller.on_batch_files_selected([str(first), str(second)])
    record = task_model.records()[0]
    record.status = TaskStatus.running
    controller.remove_task(record.task_id)

    assert task_model.records()[0] == record
    assert any("不可移除" in message for message in window.status_messages)
