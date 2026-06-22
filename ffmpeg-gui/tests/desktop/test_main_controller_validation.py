from __future__ import annotations

from pathlib import Path

from desktop.app.controllers.main_controller import MainController
from desktop.app.core.config import AppConfig
from desktop.app.runtime.binaries import RuntimeHealth
from desktop.app.runtime.ffmpeg import CommandSpec
from desktop.app.services.output_service import BatchZipResult
from desktop.app.services.sleep_inhibitor import SleepInhibitionResult
from shared.contracts import MediaInfo, Operation, STACK_MAX_ITEMS, TaskRecord, TaskStatus


class _Signal:
    def __init__(self) -> None:
        self.slots: list[object] = []

    def connect(self, *_: object, **__: object) -> None:
        self.slots.extend(_)
        return None


class _FakeWindow:
    def __init__(self) -> None:
        self._operation_payload = (Operation.convert, {}, {})
        self._selected_input_path: Path | None = None
        self._selected_batch_paths: list[Path] = []
        self._selected_output_dir = "/tmp"
        self._ffmpeg_bin = "ffmpeg"
        self._ffprobe_bin = "ffprobe"
        self._prevent_sleep_during_tasks = True
        self.stack_mode_enabled = False
        self.stack_output_options_value: dict[str, object] = {"output_format": "inherit"}
        self.batch_input_mode_enabled = False
        self.error_messages: list[str] = []
        self.status_messages: list[str] = []
        self.log_lines: list[str] = []
        self.command_preview = ""
        self.output_estimate = ""
        self.current_output_path_value: Path | None = None
        self.copied_text = ""
        self.opened_directories: list[Path] = []
        self.selected_task_ids: set[str] = set()
        self.start_enabled_values: list[bool] = []
        self.zip_results_enabled_values: list[tuple[bool, bool]] = []
        self.recent_batch_summaries: list[tuple[str, str, bool, bool]] = []
        self.batch_progress_values: list[tuple[int, int, str | None]] = []
        self.preview_records: list[TaskRecord] = []
        self.preview_operation: Operation = Operation.convert
        self.preview_trim_start: float | None = None
        self.preview_trim_end: float | None = None
        self.preview_thumbnail_timestamp: float | None = None

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
        self.task_selected = _Signal()
        self.preview_trim_start_requested = _Signal()
        self.preview_trim_end_requested = _Signal()
        self.preview_trim_clear_requested = _Signal()
        self.preview_thumbnail_time_requested = _Signal()
        self.open_output_requested = _Signal()
        self.open_output_dir_requested = _Signal()
        self.zip_outputs_requested = _Signal()
        self.copy_batch_output_paths_requested = _Signal()
        self.open_batch_output_dir_requested = _Signal()
        self.locate_batch_results_requested = _Signal()
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

    def prevent_sleep_during_tasks(self) -> bool:
        return self._prevent_sleep_during_tasks

    def set_prevent_sleep_during_tasks(self, enabled: bool) -> None:
        self._prevent_sleep_during_tasks = enabled

    def stack_mode(self) -> bool:
        return self.stack_mode_enabled

    def stack_output_options(self) -> dict[str, object]:
        return dict(self.stack_output_options_value)

    def set_start_enabled(self, enabled: bool) -> None:
        self.start_enabled_values.append(enabled)

    def set_runtime_health(self, _health: RuntimeHealth) -> None:
        return None

    def set_media_info(self, _media_info: object) -> None:
        return None

    def set_preview_record(self, record: TaskRecord) -> None:
        self.preview_records.append(record)

    def clear_preview(self, _message: str = "暂无预览") -> None:
        self.preview_records.clear()

    def preview_task_id(self) -> str | None:
        if not self.preview_records:
            return None
        return self.preview_records[-1].task_id

    def set_preview_operation(self, operation: Operation) -> None:
        self.preview_operation = operation

    def set_trim_start_seconds(self, seconds: float) -> None:
        self.preview_trim_start = seconds

    def set_trim_end_seconds(self, seconds: float) -> None:
        self.preview_trim_end = seconds

    def clear_trim_range(self) -> None:
        self.preview_trim_start = None
        self.preview_trim_end = None

    def set_thumbnail_timestamp_seconds(self, seconds: float) -> bool:
        if self._operation_payload[0] is not Operation.thumbnail:
            return False
        self.preview_thumbnail_timestamp = seconds
        return True

    def show_error(self, message: str) -> None:
        self.error_messages.append(message)

    def show_status(self, message: str) -> None:
        self.status_messages.append(message)

    def set_stack_items(self, items: list[str]) -> None:
        self._stack_items = items

    def set_batch_progress(self, current: int, total: int, *, terminal_label: str | None = None) -> None:
        self.batch_progress_values.append((current, total, terminal_label))

    def set_progress(self, *_: object) -> None:
        return None

    def reset_progress(self) -> None:
        return None

    def set_busy(self, *_: object) -> None:
        return None

    def set_current_output(self, _path: Path | None) -> None:
        self.current_output_path_value = _path

    def set_zip_results_enabled(self, enabled: bool, *, running: bool = False) -> None:
        self.zip_results_enabled_values.append((enabled, running))

    def set_recent_batch_results(
        self,
        summary: str,
        *,
        tooltip: str,
        has_batch: bool,
        has_successful_outputs: bool,
    ) -> None:
        self.recent_batch_summaries.append((summary, tooltip, has_batch, has_successful_outputs))

    def copy_text_to_clipboard(self, text: str) -> None:
        self.copied_text = text

    def open_directory(self, directory: Path) -> None:
        self.opened_directories.append(directory)

    def select_task_ids(self, task_ids: set[str]) -> int:
        self.selected_task_ids = set(task_ids)
        return len(task_ids)

    def set_command_preview(self, command: str) -> None:
        self.command_preview = command

    def set_output_estimate(self, estimate: str) -> None:
        self.output_estimate = estimate

    def clear_log(self) -> None:
        return None

    def append_log(self, line: str) -> None:
        self.log_lines.append(line)

    def set_batch_buttons(self, *_: object, **__: object) -> None:
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
        self.build_command_args: list[tuple[object, ...]] = []
        self.build_command_kwargs: list[dict[str, object]] = []

    def check_health(self, *_: str) -> RuntimeHealth:
        return self._health

    def build_command(self, *_: object, **kwargs: object) -> CommandSpec:
        self.build_command_args.append(_)
        self.build_command_kwargs.append(kwargs)
        return CommandSpec(args=["ffmpeg", "-i", "input_placeholder", "out.mp4"], output_path=Path("/tmp/out.mp4"), output_name="out.mp4")


class _OutputService:
    def normalize_output_dir(self, path: Path | str) -> Path:
        return Path(path)

    def default_output_dir(self) -> Path:
        return Path("/tmp")

    def zip_successful_outputs(self, *_: object, **__: object) -> BatchZipResult:
        return BatchZipResult(archive_path=Path("/tmp/ffmpeg-gui-batch-test.zip"), packed_count=1, skipped_count=0)


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

    def cancel_current(self, *_: object, **__: object) -> None:
        return None

    def create_worker(self, *_: object, **__: object) -> object:
        raise AssertionError("should not reach worker creation")


class _SleepInhibitor:
    def __init__(self, result: SleepInhibitionResult | None = None) -> None:
        self.result = result or SleepInhibitionResult(supported=True, active=True, changed=True)
        self.enabled_values: list[bool] = []
        self.start_count = 0
        self.stop_count = 0

    def set_enabled(self, enabled: bool) -> None:
        self.enabled_values.append(enabled)

    def start(self) -> SleepInhibitionResult:
        self.start_count += 1
        return self.result

    def stop(self) -> None:
        self.stop_count += 1


class _FakeWorker:
    def __init__(self) -> None:
        self.status_changed = _Signal()
        self.progress_changed = _Signal()
        self.log_received = _Signal()
        self.result_ready = _Signal()
        self.error_occurred = _Signal()
        self.finished = _Signal()
        self.started = False

    def start(self) -> None:
        self.started = True


class _RecordingTaskManager(_TaskManager):
    def __init__(self) -> None:
        self.created_workers: list[tuple[CommandSpec, float | None, _FakeWorker]] = []

    def create_worker(self, spec: CommandSpec, duration: float | None) -> object:
        worker = _FakeWorker()
        self.created_workers.append((spec, duration, worker))
        return worker


def _make_controller(
    window: _FakeWindow,
    task_model: _TaskModel | None = None,
    ffmpeg_service: _FfmpegService | None = None,
    task_manager: _TaskManager | None = None,
    sleep_inhibitor: _SleepInhibitor | None = None,
) -> MainController:
    ffmpeg_service = ffmpeg_service or _FfmpegService(
        RuntimeHealth(
            ok=True,
            ffmpeg_available=True,
            ffprobe_available=True,
            ffmpeg_path="ffmpeg",
            ffprobe_path="ffprobe",
        )
    )
    return MainController(
        window=window,
        task_model=task_model or _TaskModel(),
        config_service=_ConfigService(),
        ffmpeg_service=ffmpeg_service,
        output_service=_OutputService(),
        log_service=_LogService(),
        sleep_inhibitor=sleep_inhibitor or _SleepInhibitor(),
        task_manager=task_manager or _TaskManager(),
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


def test_start_task_rejects_fade_out_before_media_duration(tmp_path: Path) -> None:
    window = _FakeWindow()
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"\x00")
    window.set_operation_payload(Operation.fade, {"fade_out_seconds": 0.5, "output_format": "mp4"}, {})
    window.set_input_path(input_path)

    controller = _make_controller(window)
    controller.state.input_path = input_path
    controller.start_task()

    assert any("淡出需要先读取媒体时长" in message for message in window.error_messages)


def test_fade_out_options_use_media_duration(tmp_path: Path) -> None:
    window = _FakeWindow()
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"\x00")
    controller = _make_controller(window)
    controller.state.input_path = input_path
    controller.state.media_info = MediaInfo(raw={}, duration_seconds=7.5)

    options = controller._options_with_media_duration(
        Operation.fade,
        {"fade_out_seconds": 0.5, "output_format": "mp4"},
        input_path,
    )

    assert options["duration_seconds"] == 7.5


def test_single_task_starts_and_stops_sleep_inhibitor(tmp_path: Path) -> None:
    window = _FakeWindow()
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"\x00")
    window.set_input_path(input_path)
    task_manager = _RecordingTaskManager()
    sleep_inhibitor = _SleepInhibitor()
    controller = _make_controller(window, task_manager=task_manager, sleep_inhibitor=sleep_inhibitor)
    controller.state.input_path = input_path

    controller.start_task()

    assert sleep_inhibitor.start_count == 1
    assert any("长任务防睡眠已启用" in message for message in window.status_messages)
    current_task = controller.state.current_task
    assert current_task is not None
    controller._on_task_finished(current_task, task_manager.created_workers[0][2], TaskStatus.succeeded)

    assert sleep_inhibitor.stop_count == 1


def test_sleep_inhibitor_disabled_by_setting_does_not_start(tmp_path: Path) -> None:
    window = _FakeWindow()
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"\x00")
    window.set_input_path(input_path)
    window.set_prevent_sleep_during_tasks(False)
    sleep_inhibitor = _SleepInhibitor()
    controller = _make_controller(window, task_manager=_RecordingTaskManager(), sleep_inhibitor=sleep_inhibitor)
    controller.state.input_path = input_path

    controller.start_task()

    assert sleep_inhibitor.enabled_values[-1] is False
    assert sleep_inhibitor.start_count == 0


def test_sleep_inhibitor_failure_does_not_block_task(tmp_path: Path) -> None:
    window = _FakeWindow()
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"\x00")
    window.set_input_path(input_path)
    task_manager = _RecordingTaskManager()
    sleep_inhibitor = _SleepInhibitor(SleepInhibitionResult(supported=True, active=False, error="boom"))
    controller = _make_controller(window, task_manager=task_manager, sleep_inhibitor=sleep_inhibitor)
    controller.state.input_path = input_path

    controller.start_task()

    assert len(task_manager.created_workers) == 1
    assert any("长任务防睡眠启用失败" in message for message in window.status_messages)


def test_batch_fade_out_uses_per_file_media_duration(tmp_path: Path) -> None:
    window = _FakeWindow()
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    first.write_bytes(b"\x00")
    second.write_bytes(b"\x00")
    window.set_operation_payload(Operation.fade, {"fade_out_seconds": 0.5, "output_format": "mp4"}, {})
    window.set_batch_paths([first, second])
    window.set_batch_input_mode(True)
    service = _FfmpegService(
        RuntimeHealth(
            ok=True,
            ffmpeg_available=True,
            ffprobe_available=True,
            ffmpeg_path="ffmpeg",
            ffprobe_path="ffprobe",
        )
    )
    task_manager = _RecordingTaskManager()
    controller = _make_controller(window, ffmpeg_service=service, task_manager=task_manager)
    controller.state.input_mode = "batch"
    controller.state.batch_input_paths = [first, second]
    controller.state.input_path = first
    controller._cache_media_info(first, MediaInfo(raw={"streams": [{"codec_type": "video", "width": 640, "height": 360}]}, duration_seconds=5.0))
    controller._cache_media_info(second, MediaInfo(raw={"streams": [{"codec_type": "video", "width": 640, "height": 360}]}, duration_seconds=8.0))
    controller.start_task()

    first_request = service.build_command_args[0][1]
    assert first_request.options["duration_seconds"] == 5.0
    assert task_manager.created_workers[0][1] == 5.0

    first_record = controller.state.current_task
    assert first_record is not None
    controller._on_task_finished(first_record, task_manager.created_workers[0][2], TaskStatus.succeeded)

    second_request = service.build_command_args[1][1]
    assert second_request.options["duration_seconds"] == 8.0
    assert task_manager.created_workers[1][1] == 8.0


def test_batch_task_keeps_one_sleep_inhibitor_for_continuous_queue(tmp_path: Path) -> None:
    window = _FakeWindow()
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    first.write_bytes(b"\x00")
    second.write_bytes(b"\x00")
    window.set_operation_payload(Operation.convert, {"output_format": "mp4"}, {})
    window.set_batch_paths([first, second])
    window.set_batch_input_mode(True)
    task_manager = _RecordingTaskManager()
    sleep_inhibitor = _SleepInhibitor()
    controller = _make_controller(window, task_manager=task_manager, sleep_inhibitor=sleep_inhibitor)
    controller.state.input_mode = "batch"
    controller.state.batch_input_paths = [first, second]
    controller.state.input_path = first

    controller.start_task()

    assert sleep_inhibitor.start_count == 1
    first_record = controller.state.current_task
    assert first_record is not None
    controller._on_task_finished(first_record, task_manager.created_workers[0][2], TaskStatus.succeeded)

    assert sleep_inhibitor.start_count == 1
    assert sleep_inhibitor.stop_count == 0
    second_record = controller.state.current_task
    assert second_record is not None
    controller._on_task_finished(second_record, task_manager.created_workers[1][2], TaskStatus.succeeded)

    assert sleep_inhibitor.start_count == 1
    assert sleep_inhibitor.stop_count == 1


def test_close_stops_sleep_inhibitor() -> None:
    window = _FakeWindow()
    sleep_inhibitor = _SleepInhibitor()
    controller = _make_controller(window, sleep_inhibitor=sleep_inhibitor)

    controller.close()

    assert sleep_inhibitor.stop_count >= 1


def test_media_info_operation_writes_probe_json_to_log(tmp_path: Path) -> None:
    window = _FakeWindow()
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"\x00")
    window.set_operation_payload(Operation.media_info, {}, {})
    window.set_input_path(input_path)
    task_model = _TaskModel()

    controller = _make_controller(window, task_model=task_model)
    controller.state.input_path = input_path
    controller.state.media_info = MediaInfo(raw={"format": {"duration": "1.0"}}, duration_seconds=1.0)
    controller.start_task()

    assert task_model.records()[0].status is TaskStatus.succeeded
    assert task_model.records()[0].operation is Operation.media_info
    assert any("ffprobe" in line for line in window.log_lines)
    assert any('"duration": "1.0"' in line for line in window.log_lines)
    assert any("媒体信息已写入日志" in message for message in window.status_messages)


def test_media_info_preview_uses_ffprobe_command() -> None:
    window = _FakeWindow()
    window.set_operation_payload(Operation.media_info, {}, {})
    controller = _make_controller(window)

    controller._refresh_command_preview()

    assert window.command_preview.startswith("$ ffprobe -v error")
    assert "不生成文件" in window.output_estimate


def test_command_preview_skips_runtime_capability_validation(tmp_path: Path) -> None:
    window = _FakeWindow()
    subtitle_path = tmp_path / "caption.srt"
    subtitle_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")
    window.set_operation_payload(
        Operation.subtitles,
        {"mode": "burn", "output_format": "mp4", "font_size": "medium"},
        {"subtitle": subtitle_path},
    )
    service = _FfmpegService(
        RuntimeHealth(
            ok=True,
            ffmpeg_available=True,
            ffprobe_available=True,
            ffmpeg_path="ffmpeg",
            ffprobe_path="ffprobe",
        )
    )
    controller = _make_controller(window, ffmpeg_service=service)

    controller._refresh_command_preview()

    assert service.build_command_kwargs[-1]["validate_capabilities"] is False


def test_output_estimate_treats_bitrate_as_bits_per_second() -> None:
    window = _FakeWindow()
    controller = _make_controller(window)
    controller.state.input_path = Path("/tmp/input.mp4")
    controller.state.media_info = MediaInfo(raw={}, duration_seconds=8.0)
    spec = CommandSpec(args=[], output_path=Path("/tmp/out.mp4"), output_name="out.mp4")

    estimate = controller._format_output_estimate(spec)

    assert "4.77 MB" in estimate


def test_stack_add_reports_unsupported_subtitle_operation(tmp_path: Path) -> None:
    window = _FakeWindow()
    window.set_operation_payload(Operation.subtitles, {"mode": "soft"}, {})
    controller = _make_controller(window)

    controller._on_stack_add_requested()

    assert any("当前动作不支持加入 Stack" in message for message in window.error_messages)
    assert controller._stack_items == []


def test_stack_add_ignores_more_than_max_items_without_popup() -> None:
    window = _FakeWindow()
    window.stack_mode_enabled = True
    window.set_operation_payload(Operation.rotate, {"mode": "cw90", "output_format": "mp4"}, {})
    controller = _make_controller(window)

    for _ in range(STACK_MAX_ITEMS):
        controller._on_stack_add_requested()
    controller._on_stack_add_requested()

    assert len(controller._stack_items) == STACK_MAX_ITEMS
    assert len(window._stack_items) == STACK_MAX_ITEMS
    assert window.error_messages == []


def test_stack_batch_start_state_allows_crop_step(tmp_path: Path) -> None:
    window = _FakeWindow()
    window.stack_mode_enabled = True
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    first.write_bytes(b"\x00")
    second.write_bytes(b"\x00")
    window.set_operation_payload(
        Operation.crop,
        {"x": 0, "y": 0, "width": 320, "height": 180, "output_format": "mp4"},
        {},
    )
    window.set_batch_paths([first, second])
    task_model = _TaskModel()
    controller = _make_controller(window, task_model=task_model)
    controller._on_stack_add_requested()
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

    controller._refresh_start_state()

    assert window.start_enabled_values[-1] is True
    assert not any("Stack 批处理暂不支持" in message for message in window.status_messages)


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

    assert window._stack_items == ["旋转翻转 · 顺90 · MP4", "裁剪 · 320x180+4+8 · MP4"]
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


def test_stack_batch_crop_skips_file_when_crop_exceeds_resolution(tmp_path: Path) -> None:
    window = _FakeWindow()
    window.stack_mode_enabled = True
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    first.write_bytes(b"\x00")
    second.write_bytes(b"\x00")
    window.set_operation_payload(
        Operation.crop,
        {"x": 0, "y": 0, "width": 500, "height": 300, "output_format": "mp4"},
        {},
    )
    window.set_batch_paths([first, second])
    task_model = _TaskModel()
    task_manager = _RecordingTaskManager()

    controller = _make_controller(window, task_model=task_model, task_manager=task_manager)
    controller._on_stack_add_requested()
    controller.state.input_mode = "batch"
    controller.state.batch_input_paths = [first, second]
    controller.state.input_path = first
    controller._cache_media_info(first, MediaInfo(raw={"streams": [{"codec_type": "video", "width": 640, "height": 360}]}, duration_seconds=5.0))
    controller._cache_media_info(second, MediaInfo(raw={"streams": [{"codec_type": "video", "width": 320, "height": 180}]}, duration_seconds=5.0))
    window.set_batch_input_mode(True)
    controller.start_task()

    assert len(task_manager.created_workers) == 1
    first_record = controller.state.current_task
    assert first_record is not None
    controller._on_task_finished(first_record, task_manager.created_workers[0][2], TaskStatus.succeeded)

    records = task_model.records()
    assert records[0].status is TaskStatus.succeeded
    assert records[1].status is TaskStatus.failed
    assert "裁剪区域超出文件分辨率" in records[1].message
    assert window.batch_progress_values[-1] == (2, 2, "处理结束（有失败）")


def test_batch_stack_applies_stack_gif_output_options_to_each_file(tmp_path: Path) -> None:
    window = _FakeWindow()
    window.stack_mode_enabled = True
    window.stack_output_options_value = {"output_format": "gif", "quality": "fast", "fps": 8, "width": 240}
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    first.write_bytes(b"\x00")
    second.write_bytes(b"\x00")
    window.set_operation_payload(Operation.rotate, {"mode": "cw90", "output_format": "mp4"}, {})
    window.set_batch_paths([first, second])
    task_manager = _RecordingTaskManager()

    controller = _make_controller(window, task_manager=task_manager)
    controller._on_stack_add_requested()
    controller.state.input_mode = "batch"
    controller.state.batch_input_paths = [first, second]
    controller.state.input_path = first
    window.set_batch_input_mode(True)
    controller.start_task()

    assert len(task_manager.created_workers) == 1
    first_spec = task_manager.created_workers[0][0]
    assert first_spec.output_path is not None
    assert first_spec.output_path.suffix == ".gif"
    assert "fps=8,scale=240" in first_spec.args[first_spec.args.index("-vf") + 1]

    first_record = controller.state.current_task
    assert first_record is not None
    controller._on_task_finished(first_record, task_manager.created_workers[0][2], TaskStatus.succeeded)

    assert len(task_manager.created_workers) == 2
    second_spec = task_manager.created_workers[1][0]
    assert second_spec.output_path is not None
    assert second_spec.output_path.suffix == ".gif"
    assert "fps=8,scale=240" in second_spec.args[second_spec.args.index("-vf") + 1]


def test_finish_batch_reports_cancelled_terminal_label() -> None:
    window = _FakeWindow()
    controller = _make_controller(window)
    controller.state.is_batch_running = True
    controller.state.batch_current_index = 1
    controller._current_batch_total = 3
    controller._batch_records = [
        TaskRecord(operation=Operation.convert, input_path=Path("/tmp/first.mp4"), status=TaskStatus.cancelled),
    ]

    controller._finish_batch(TaskStatus.cancelled)

    assert window.batch_progress_values[-1] == (1, 3, "处理已取消")


def test_finish_batch_reports_partial_failure_terminal_label() -> None:
    window = _FakeWindow()
    controller = _make_controller(window)
    controller.state.is_batch_running = True
    controller.state.batch_current_index = 3
    controller._current_batch_total = 3
    controller._batch_records = [
        TaskRecord(operation=Operation.convert, input_path=Path("/tmp/failed.mp4"), status=TaskStatus.failed),
    ]

    controller._finish_batch(TaskStatus.failed)

    assert window.batch_progress_values[-1] == (3, 3, "处理结束（有失败）")


def test_finish_batch_enables_zip_results_for_last_batch(tmp_path: Path) -> None:
    window = _FakeWindow()
    output_path = tmp_path / "out.mp4"
    output_path.write_bytes(b"ok")
    task_model = _TaskModel()
    record = TaskRecord(
        operation=Operation.convert,
        input_path=tmp_path / "input.mp4",
        output_path=output_path,
        status=TaskStatus.succeeded,
        progress=1.0,
    )
    task_model.append_record(record)
    controller = _make_controller(window, task_model=task_model)
    controller.state.is_batch_running = True
    controller.state.batch_current_index = 1
    controller._current_batch_total = 1
    controller._batch_records = [record]
    controller.state.recent_batch.task_ids = {record.task_id}

    controller._finish_batch()

    assert window.zip_results_enabled_values[-1] == (True, False)
    assert window.recent_batch_summaries[-1][0] == "最近批次：成功 1 · 失败 0 · 取消 0 · 已打包 0"


def test_zip_batch_outputs_without_current_batch_reports_status() -> None:
    window = _FakeWindow()
    controller = _make_controller(window)

    controller.zip_batch_outputs()

    assert window.status_messages[-1] == "当前没有可打包的批量结果"


def test_zip_result_updates_status_and_current_output(tmp_path: Path) -> None:
    window = _FakeWindow()
    controller = _make_controller(window)
    archive_path = tmp_path / "ffmpeg-gui-batch-20260621-101112.zip"

    controller._on_zip_results_ready(BatchZipResult(archive_path=archive_path, packed_count=2, skipped_count=1))

    assert window.current_output_path_value == archive_path
    assert window.status_messages[-1] == "已打包 2 个，跳过 1 个：ffmpeg-gui-batch-20260621-101112.zip"
    assert window.recent_batch_summaries[-1][0] == "最近批次：暂无结果"


def test_zip_thread_starts_and_stops_sleep_inhibitor(monkeypatch, tmp_path: Path) -> None:
    import desktop.app.controllers.main_controller as main_controller_module

    class _FakeZipThread:
        def __init__(self) -> None:
            self.started = _Signal()
            self.finished = _Signal()
            self.started_count = 0
            self.quit_count = 0
            self.wait_count = 0

        def start(self) -> None:
            self.started_count += 1

        def isRunning(self) -> bool:
            return True

        def quit(self) -> None:
            self.quit_count += 1

        def wait(self, _wait_msecs: int) -> None:
            self.wait_count += 1

        def deleteLater(self) -> None:
            return None

    class _FakeZipWorker:
        def __init__(self, *_: object) -> None:
            self.result_ready = _Signal()
            self.error_occurred = _Signal()
            self.finished = _Signal()
            self.cancel_count = 0

        def moveToThread(self, _thread: object) -> None:
            return None

        def run(self) -> None:
            return None

        def cancel(self) -> None:
            self.cancel_count += 1

        def deleteLater(self) -> None:
            return None

    fake_thread = _FakeZipThread()
    monkeypatch.setattr(main_controller_module, "QThread", lambda: fake_thread)
    monkeypatch.setattr(main_controller_module, "ZipResultsWorker", _FakeZipWorker)
    window = _FakeWindow()
    sleep_inhibitor = _SleepInhibitor()
    controller = _make_controller(window, sleep_inhibitor=sleep_inhibitor)
    record = TaskRecord(
        operation=Operation.convert,
        input_path=tmp_path / "input.mp4",
        output_path=tmp_path / "out.mp4",
        status=TaskStatus.succeeded,
    )

    controller._start_zip_thread([record], tmp_path)

    assert sleep_inhibitor.start_count == 1
    assert window.zip_results_enabled_values[-1] == (False, True)
    assert window.status_messages[-1] == "长任务防睡眠已启用"
    assert fake_thread.started_count == 1

    controller._stop_zip_thread()

    assert sleep_inhibitor.stop_count == 1
    assert fake_thread.quit_count == 1
    assert fake_thread.wait_count == 1


def test_copy_recent_batch_output_paths_only_uses_successful_existing_outputs(tmp_path: Path) -> None:
    window = _FakeWindow()
    output_path = tmp_path / "out one.mp4"
    output_path.write_bytes(b"ok")
    missing_path = tmp_path / "missing.mp4"
    task_model = _TaskModel()
    success = TaskRecord(
        operation=Operation.convert,
        input_path=tmp_path / "in one.mp4",
        output_path=output_path,
        status=TaskStatus.succeeded,
    )
    missing = TaskRecord(
        operation=Operation.convert,
        input_path=tmp_path / "in two.mp4",
        output_path=missing_path,
        status=TaskStatus.succeeded,
    )
    failed = TaskRecord(
        operation=Operation.convert,
        input_path=tmp_path / "in three.mp4",
        output_path=tmp_path / "failed.mp4",
        status=TaskStatus.failed,
    )
    for record in (success, missing, failed):
        task_model.append_record(record)
    controller = _make_controller(window, task_model=task_model)
    controller.state.recent_batch.task_ids = {success.task_id, missing.task_id, failed.task_id}

    controller.copy_recent_batch_output_paths()

    assert window.copied_text == str(output_path)
    assert window.status_messages[-1] == "已复制 1 个成功输出路径"


def test_open_recent_batch_output_dir_uses_state_output_dir(tmp_path: Path) -> None:
    window = _FakeWindow()
    task_model = _TaskModel()
    record = TaskRecord(
        operation=Operation.convert,
        input_path=tmp_path / "input.mp4",
        output_path=tmp_path / "out.mp4",
        status=TaskStatus.succeeded,
    )
    task_model.append_record(record)
    controller = _make_controller(window, task_model=task_model)
    controller.state.output_dir = tmp_path
    controller.state.recent_batch.task_ids = {record.task_id}

    controller.open_recent_batch_output_dir()

    assert window.opened_directories == [tmp_path]
    assert window.status_messages[-1] == f"已打开最近批次输出目录：{tmp_path}"


def test_locate_recent_batch_results_selects_task_ids() -> None:
    window = _FakeWindow()
    controller = _make_controller(window)
    controller.state.recent_batch.task_ids = {"a", "b"}

    controller.locate_recent_batch_results()

    assert window.selected_task_ids == {"a", "b"}
    assert window.status_messages[-1] == "已定位最近批次 2 条结果"


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


def test_batch_selection_probes_each_added_file_in_sequence(tmp_path: Path) -> None:
    window = _FakeWindow()
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mov"
    first.write_bytes(b"\x00")
    second.write_bytes(b"\x00")
    task_model = _TaskModel()
    controller = _make_controller(window, task_model=task_model)
    controller.state.runtime_health = RuntimeHealth(
        ok=True,
        ffmpeg_available=True,
        ffprobe_available=True,
        ffmpeg_path="ffmpeg",
        ffprobe_path="ffprobe",
    )
    started: list[tuple[Path, str, str | None]] = []

    def fake_start_probe(
        path: Path,
        *,
        context: str = "direct",
        batch_record: TaskRecord | None = None,
        selection_record: TaskRecord | None = None,
    ) -> None:
        del batch_record
        started.append((path, context, selection_record.task_id if selection_record else None))

    controller._start_probe = fake_start_probe  # type: ignore[method-assign]

    controller.on_batch_files_selected([str(first), str(second)])

    records = task_model.records()
    assert [record.input_path for record in records] == [first, second]
    assert records[0].status is TaskStatus.probing
    assert records[1].status is TaskStatus.ready
    assert started == [(first, "selection", records[0].task_id)]

    controller._on_selection_media_info(
        first,
        MediaInfo(
            raw={
                "streams": [
                    {"codec_type": "video", "height": 1080, "codec_name": "h264"},
                    {"codec_type": "audio", "codec_name": "aac"},
                ]
            },
            duration_seconds=53.0,
        ),
    )

    assert records[0].status is TaskStatus.ready
    assert isinstance(records[0].media_info, MediaInfo)
    assert records[1].status is TaskStatus.probing
    assert started[-1] == (second, "selection", records[1].task_id)

    controller._on_selection_media_info(
        second,
        MediaInfo(
            raw={"streams": [{"codec_type": "video", "height": 720, "codec_name": "hevc"}]},
            duration_seconds=12.0,
        ),
    )

    assert records[1].status is TaskStatus.ready
    assert isinstance(records[1].media_info, MediaInfo)


def test_appending_file_after_single_selection_probes_new_record(tmp_path: Path) -> None:
    window = _FakeWindow()
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mov"
    first.write_bytes(b"\x00")
    second.write_bytes(b"\x00")
    task_model = _TaskModel()
    controller = _make_controller(window, task_model=task_model)
    controller.state.runtime_health = RuntimeHealth(
        ok=True,
        ffmpeg_available=True,
        ffprobe_available=True,
        ffmpeg_path="ffmpeg",
        ffprobe_path="ffprobe",
    )
    started: list[Path] = []

    def fake_start_probe(
        path: Path,
        *,
        context: str = "direct",
        batch_record: TaskRecord | None = None,
        selection_record: TaskRecord | None = None,
    ) -> None:
        del context, batch_record, selection_record
        started.append(path)

    controller._start_probe = fake_start_probe  # type: ignore[method-assign]

    controller.on_batch_files_selected([str(first)])
    first_record = task_model.records()[0]
    controller._on_selection_media_info(first, MediaInfo(raw={"streams": []}, duration_seconds=53.0))
    controller.on_batch_files_selected([str(second)])

    records = task_model.records()
    assert [record.input_path for record in records] == [first, second]
    assert records[0] is first_record
    assert isinstance(records[0].media_info, MediaInfo)
    assert records[1].status is TaskStatus.probing
    assert started == [first, second]


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
    assert window.preview_records[0].input_path == first


def test_preview_actions_write_back_parameters_and_refresh_preview() -> None:
    window = _FakeWindow()
    controller = _make_controller(window)

    controller._apply_preview_trim_start(1.25)
    controller._apply_preview_trim_end(3.5)
    controller._clear_preview_trim_range()
    window.set_operation_payload(Operation.thumbnail, {"image_format": "jpg"}, {})
    controller._apply_preview_thumbnail_time(2.0)

    assert window.preview_trim_start is None
    assert window.preview_trim_end is None
    assert window.preview_thumbnail_timestamp == 2.0
    assert any("已设置开始时间：1.25" in message for message in window.status_messages)
    assert any("已清空处理范围" in message for message in window.status_messages)
    assert window.preview_operation is Operation.thumbnail


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
