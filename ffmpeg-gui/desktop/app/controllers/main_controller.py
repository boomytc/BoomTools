from __future__ import annotations

import shlex
from pathlib import Path

from PySide6.QtCore import QThread

from desktop.app.core.config import AppConfig
from desktop.app.runtime.ffmpeg import CommandError, CommandSpec
from desktop.app.runtime.filter_chain import STACK_FILTER_OPERATIONS, build_stack_command
from desktop.app.services.config_service import ConfigService
from desktop.app.services.ffmpeg_service import FfmpegService
from desktop.app.services.log_service import LogService
from desktop.app.services.output_service import OutputService
from desktop.app.tasks.probe_worker import ProbeWorker
from desktop.app.tasks.task_manager import TaskManager
from desktop.app.ui.main_window import MainWindow
from desktop.app.ui.widgets.task_table_model import TaskTableModel
from desktop.app.viewmodels.app_state import AppState
from desktop.app.viewmodels.task_state import TaskState
from shared.contracts import MediaInfo, Operation, TaskRecord, TaskRequest, TaskResult, TaskStatus, operation_label


SUBTITLE_EXTENSIONS = {".srt", ".vtt", ".ass", ".ssa"}
BATCH_SUPPORTED_OPERATIONS = {
    Operation.convert,
    Operation.compress,
    Operation.resize_compress,
    Operation.extract_audio,
    Operation.gif,
    Operation.mute,
    Operation.speed,
    Operation.rotate,
    Operation.fade,
    Operation.adjust,
    Operation.strip_metadata,
    Operation.loop,
    Operation.pad,
    Operation.normalize_audio,
    Operation.volume,
    Operation.denoise,
    Operation.sharpen_blur,
}


class MainController:
    def __init__(
        self,
        window: MainWindow,
        task_model: TaskTableModel,
        *,
        config_service: ConfigService,
        ffmpeg_service: FfmpegService,
        output_service: OutputService,
        log_service: LogService,
        task_manager: TaskManager,
    ) -> None:
        self.window = window
        self.task_model = task_model
        self.config_service = config_service
        self.ffmpeg_service = ffmpeg_service
        self.output_service = output_service
        self.log_service = log_service
        self.task_manager = task_manager

        self.state = AppState()
        self.task_state = TaskState()
        self._probe_thread: QThread | None = None
        self._probe_worker: ProbeWorker | None = None

        self._batch_queue: list[tuple[TaskRecord, Path]] = []
        self._batch_operation: Operation = Operation.convert
        self._batch_options: dict[str, object] = {}
        self._batch_extra_inputs: dict[str, Path] = {}
        self._batch_stack_items: list[tuple[Operation, dict[str, object], dict[str, Path]]] = []
        self._is_batch_stack_mode: bool = False
        self._pending_total: int = 0
        self._current_batch_total: int = 0
        self._stack_items: list[tuple[Operation, dict[str, object], dict[str, Path]]] = []

        self._connect_signals()

    def initialize(self) -> None:
        config = self.config_service.load()
        output_dir = self.output_service.normalize_output_dir(config.output_dir)
        self.window.set_initial_paths(
            ffmpeg_bin=config.ffmpeg_bin,
            ffprobe_bin=config.ffprobe_bin,
            output_dir=output_dir,
        )
        self.state.output_dir = output_dir
        self.refresh_runtime_health()
        self.window.set_batch_progress(0, 0)
        self.window.set_stack_items([])
        self.window.set_stack_mode(False)
        self.window.set_start_enabled(self.state.can_start())
        self.window.set_batch_buttons(pending_count=0, running=False)

    def refresh_runtime_health(self) -> None:
        self._save_current_config()
        health = self.ffmpeg_service.check_health(self.window.selected_ffmpeg_bin(), self.window.selected_ffprobe_bin())
        self.state.runtime_health = health
        self.window.set_runtime_health(health)
        self.window.set_start_enabled(self.state.can_start())
        if self.state.is_batch_running:
            self.window.set_batch_buttons(
                pending_count=len(self._batch_queue),
                running=health.ok and self.state.current_task is not None and self.state.current_task.status is TaskStatus.running,
            )

    def on_input_file_selected(self, path_text: str) -> None:
        path = Path(path_text)
        self.state.input_path = path
        self.state.media_info = None
        self.state.batch_input_paths = []
        self.window.set_media_info(None)
        self.window.reset_progress()
        self.window.set_current_output(None)
        self.window.set_start_enabled(False)
        self.window.set_batch_progress(0, 0)
        if not path.exists():
            self.window.show_error("输入文件不存在")
            return
        self._start_probe(path)

    def on_batch_files_selected(self, path_texts: list[str]) -> None:
        batch_paths = [Path(path) for path in path_texts if Path(path).exists()]
        if not batch_paths:
            self.window.show_error("请选择至少一个可用文件")
            return
        self.state.batch_input_paths = batch_paths
        self.state.input_path = batch_paths[0]
        self.state.media_info = None
        self.window.set_media_info(None)
        self.window.reset_progress()
        self.window.set_current_output(None)
        self.window.set_batch_progress(0, len(batch_paths))
        self.window.set_start_enabled(True)

    def on_output_dir_selected(self, path_text: str) -> None:
        path = self.output_service.normalize_output_dir(Path(path_text))
        self.state.output_dir = path
        self._save_current_config()

    def start_task(self) -> None:
        self.refresh_runtime_health()
        try:
            output_dir = self.output_service.normalize_output_dir(self.window.selected_output_dir())
        except OSError as exc:
            self.window.show_error(f"输出目录不可写或不存在：{exc}")
            return
        self.state.output_dir = output_dir

        if not self.state.runtime_health or not self.state.runtime_health.ok:
            self.window.show_error("ffmpeg 或 ffprobe 不可用，请检查路径")
            return
        if self.state.current_task and self.state.current_task.status is TaskStatus.running:
            self.window.show_error("当前已有任务在运行")
            return

        operation, options, extra_inputs = self.window.selected_operation_payload()
        try:
            self._validate_operation_inputs(operation, extra_inputs)
        except ValueError as exc:
            self.window.show_error(str(exc))
            return
        use_stack = self.window.stack_mode()
        stack_specs = self._collect_stack_specs(operation, options, extra_inputs)
        input_paths = self._collect_input_paths()
        effective_operation = stack_specs[0][0] if use_stack and stack_specs else operation
        if not input_paths:
            self.window.show_error("请先选择存在的本机媒体文件")
            return
        if use_stack and not stack_specs:
            self.window.show_error("Stack 需要至少添加一个可链式操作")
            return

        if len(input_paths) > 1 and effective_operation not in BATCH_SUPPORTED_OPERATIONS:
            self.window.show_error("该操作不支持批处理")
            return

        if use_stack:
            self._batch_stack_items = stack_specs
            self._is_batch_stack_mode = True
            self._batch_operation = operation
            self._batch_options = options
            self._batch_extra_inputs = extra_inputs
            if len(input_paths) == 1:
                self._start_single_stack_task(input_paths[0], self._batch_stack_items, media_info=self.state.media_info)
                return

            self.state.batch_input_paths = input_paths
            self._start_batch_task(input_paths)
            return

        if len(input_paths) == 1:
            self._start_single_task(operation, options, extra_inputs, input_paths[0])
            return

        self._is_batch_stack_mode = False
        self._batch_stack_items = []
        self._batch_operation = operation
        self._batch_options = options
        self._batch_extra_inputs = extra_inputs
        self.state.batch_input_paths = input_paths
        self._pending_total = len(input_paths)
        self._current_batch_total = len(input_paths)
        self.state.batch_total_items = len(input_paths)
        self.state.batch_current_index = 0
        self.state.batch_cancel_requested = False
        self.state.is_batch_running = True
        self.task_manager.clear_batch_cancel_flag()
        self._batch_queue = []

        for input_path in input_paths:
            task = TaskRecord(operation=operation, input_path=input_path, status=TaskStatus.pending, message="Queued")
            self.task_state.add(task)
            self.task_model.append_record(task)
            self._batch_queue.append((task, input_path))

        self.window.set_progress(None)
        self.window.set_batch_progress(0, self._current_batch_total)
        self.window.set_current_output(None)
        self.window.set_batch_buttons(pending_count=len(self._batch_queue), running=True)
        self.window.set_busy(True)
        self.window.clear_log()
        self._start_next_batch_task()

    def cancel_current_task(self) -> None:
        if self.state.current_task and self.state.current_task.status is TaskStatus.running:
            self.state.current_task.status = TaskStatus.cancelled
            self.state.current_task.message = "Cancelling"
            self.task_model.notify_record_changed(self.state.current_task)
        self.task_manager.cancel_current()

    def cancel_batch(self) -> None:
        if not self.state.is_batch_running:
            return
        self.state.batch_cancel_requested = True
        self.task_manager.request_cancel_batch()
        self.task_manager.cancel_current()
        if self._batch_queue:
            self._mark_batch_pending(TaskStatus.cancelled, "Cancelled")

    def remove_pending_batch_tasks(self) -> None:
        if not self._batch_queue:
            return
        self._remove_pending_records([record for record, _ in self._batch_queue])
        self._batch_queue.clear()
        self.state.batch_total_items = self.state.batch_current_index
        self.window.set_batch_progress(self.state.batch_current_index, self.state.batch_total_items)
        self.window.set_batch_buttons(pending_count=0, running=False)
        self.window.set_start_enabled(self.state.can_start())

    def open_output(self) -> None:
        self.window.open_output()

    def open_output_dir(self) -> None:
        self.window.open_output_dir()

    def close(self) -> None:
        self.cancel_current_task()
        self.cancel_batch()

    def copy_output_path(self) -> None:
        current_output = self.window.current_output_path()
        if not current_output:
            self.window.show_status("当前无可复制的输出路径")
            return
        self.window.copy_output_path()

    def _connect_signals(self) -> None:
        self.window.input_file_selected.connect(self.on_input_file_selected)
        self.window.batch_files_selected.connect(self.on_batch_files_selected)
        self.window.output_dir_selected.connect(self.on_output_dir_selected)
        self.window.refresh_requested.connect(self.refresh_runtime_health)
        self.window.start_requested.connect(self.start_task)
        self.window.cancel_requested.connect(self.cancel_current_task)
        self.window.cancel_queue_requested.connect(self.cancel_batch)
        self.window.remove_pending_requested.connect(self.remove_pending_batch_tasks)
        self.window.stack_mode_toggled.connect(self._on_stack_mode_toggled)
        self.window.stack_add_requested.connect(self._on_stack_add_requested)
        self.window.stack_move_up_requested.connect(self._on_stack_move_up_requested)
        self.window.stack_move_down_requested.connect(self._on_stack_move_down_requested)
        self.window.stack_remove_requested.connect(self._on_stack_remove_requested)
        self.window.stack_clear_requested.connect(self._on_stack_clear_requested)
        self.window.command_preview_requested.connect(self._refresh_command_preview)
        self.window.open_output_requested.connect(self.open_output)
        self.window.open_output_dir_requested.connect(self.open_output_dir)
        self.window.copy_output_path_requested.connect(self.copy_output_path)
        self.window.closing.connect(self.close)

    def _on_stack_mode_toggled(self, enabled: bool) -> None:
        self.window.set_stack_mode(enabled)
        self._refresh_stack_buttons()
        self._refresh_start_state()
        self._refresh_command_preview()

    def _refresh_stack_buttons(self) -> None:
        self.window._update_stack_add_enabled()
        self.window.set_stack_items([self._format_stack_item(item) for item in self._stack_items])

    def _on_stack_add_requested(self) -> None:
        operation, options, extra_inputs = self.window.selected_operation_payload()
        if operation not in STACK_FILTER_OPERATIONS:
            self.window.show_error("当前操作不支持加入 Stack")
            return
        try:
            self._validate_operation_inputs(operation, extra_inputs)
        except ValueError as exc:
            self.window.show_error(str(exc))
            return
        if self._stack_items:
            options = dict(options)
            options.pop("start_seconds", None)
            options.pop("end_seconds", None)

        self._stack_items.append((operation, options, extra_inputs))
        self.window.set_stack_items([self._format_stack_item(item) for item in self._stack_items])
        self._refresh_command_preview()

    def _on_stack_move_up_requested(self, index: int) -> None:
        if index <= 0 or index >= len(self._stack_items):
            return
        self._stack_items[index - 1], self._stack_items[index] = self._stack_items[index], self._stack_items[index - 1]
        self.window.set_stack_items([self._format_stack_item(item) for item in self._stack_items])
        self._refresh_command_preview()

    def _on_stack_move_down_requested(self, index: int) -> None:
        if index < 0 or index + 1 >= len(self._stack_items):
            return
        self._stack_items[index + 1], self._stack_items[index] = self._stack_items[index], self._stack_items[index + 1]
        self.window.set_stack_items([self._format_stack_item(item) for item in self._stack_items])
        self._refresh_command_preview()

    def _on_stack_remove_requested(self, index: int) -> None:
        if index < 0 or index >= len(self._stack_items):
            return
        self._stack_items.pop(index)
        self.window.set_stack_items([self._format_stack_item(item) for item in self._stack_items])
        self._refresh_command_preview()

    def _on_stack_clear_requested(self) -> None:
        self._stack_items = []
        self.window.set_stack_items([])
        self._refresh_command_preview()

    def _collect_stack_specs(
        self,
        operation: Operation,
        options: dict[str, object],
        extra_inputs: dict[str, Path],
    ) -> list[tuple[Operation, dict[str, object], dict[str, Path]]]:
        if not self.window.stack_mode():
            return [(operation, options, extra_inputs)]

        if self._stack_items:
            return list(self._stack_items)
        if operation not in STACK_FILTER_OPERATIONS:
            return []
        return [(operation, options, extra_inputs)]

    def _refresh_start_state(self) -> None:
        input_paths = self._collect_input_paths()
        can_start = self.state.can_start()
        batch_error = None
        if len(input_paths) > 1 and not self.window.stack_mode():
            operation, _, _ = self.window.selected_operation_payload()
            if operation not in BATCH_SUPPORTED_OPERATIONS:
                can_start = False
                batch_error = f"批处理暂不支持「{operation_label(operation)}」，请切换为 convert/compress/resize_compress/extract_audio/gif/mute/speed/rotate/fade/adjust/strip_metadata/volume/loop/pad/normalize_audio/denoise/sharpen_blur 后重试。"
        if self.window.stack_mode():
            try:
                can_stack = bool(self._collect_stack_specs(*self.window.selected_operation_payload()))
            except (ValueError, OSError, CommandError):
                can_stack = False
            can_start = can_start and can_stack
            batch_error = None

        if batch_error:
            self.window.show_status(batch_error)
        self.window.set_start_enabled(can_start)

    def _refresh_command_preview(self) -> None:
        try:
            operation, options, extra_inputs = self.window.selected_operation_payload()
            if self.window.stack_mode():
                stack_specs = self._collect_stack_specs(operation, options, extra_inputs)
                if not stack_specs:
                    self.window.set_command_preview("Stack 不支持当前操作")
                    self.window.set_output_estimate("输出大小保守估算：当前操作不支持 Stack")
                    return
                spec = build_stack_command(
                    ffmpeg_bin=self.window.selected_ffmpeg_bin(),
                    input_path=Path("input_placeholder"),
                    output_dir=self.output_service.default_output_dir(),
                    stack=stack_specs,
                    media_info=self.state.media_info,
                )
            else:
                spec = self.ffmpeg_service.build_command(
                    self.window.selected_ffmpeg_bin(),
                    TaskRequest(
                        input_path=Path("input_placeholder"),
                        output_dir=self.output_service.default_output_dir(),
                        operation=operation,
                        options=options,
                        extra_inputs=extra_inputs,
                    ),
                )
        except (CommandError, ValueError, OSError) as exc:
            self.window.set_command_preview(f"预览失败：{exc}")
            self.window.set_output_estimate("输出大小保守估算：参数异常，无法估算")
            return

        self.window.set_command_preview("$ " + " ".join(shlex.quote(arg) for arg in spec.args))
        self.window.set_output_estimate(self._format_output_estimate(spec))

    def _format_output_estimate(self, spec: CommandSpec) -> str:
        if spec.output_path is None:
            return "输出大小保守估算：此命令不生成文件"
        if not self.state.media_info or not self.state.media_info.duration_seconds:
            return "输出大小保守估算：等待媒体时长后估算"

        bitrate = self._estimate_bitrate(spec.output_path.suffix)
        if bitrate is None:
            return "输出大小保守估算：当前格式不支持估算"
        size_bytes = int(self.state.media_info.duration_seconds * bitrate)
        return f"输出大小保守估算：{self._format_bytes(size_bytes)}"

    def _estimate_bitrate(self, suffix: str) -> int | None:
        return {
            ".mp4": 5_000_000,
            ".mkv": 5_000_000,
            ".mov": 5_000_000,
            ".avi": 4_000_000,
            ".webm": 3_000_000,
            ".gif": 2_000_000,
            ".mp3": 192_000,
            ".wav": 1_411_200,
            ".aac": 192_000,
            ".flac": 700_000,
            ".ogg": 160_000,
        }.get(suffix.lower())

    def _format_bytes(self, size: int) -> str:
        if size <= 0:
            return "0 B"
        units = ["B", "KB", "MB", "GB", "TB"]
        size_float = float(size)
        for unit in units:
            if size_float < 1024 or unit == units[-1]:
                return f"{size_float:.2f} {unit}".rstrip("0").rstrip(".")
            size_float /= 1024

    def _format_stack_item(
        self,
        item: tuple[Operation, dict[str, object], dict[str, Path]],
    ) -> str:
        operation, options, _ = item

        if operation is Operation.resize_compress:
            extra = f"{options.get('width', 'auto')}x{options.get('height', 'auto')}"
        else:
            extra = ""
        if extra:
            return f"{operation_label(operation)} ({extra})"
        return operation_label(operation)

    def _start_single_task(
        self,
        operation: Operation,
        options: dict[str, object],
        extra_inputs: dict[str, Path],
        input_path: Path,
    ) -> None:
        try:
            spec = self.ffmpeg_service.build_command(
                self.window.selected_ffmpeg_bin(),
                TaskRequest(
                    input_path=input_path,
                    output_dir=self.state.output_dir,
                    operation=operation,
                    options=options,
                    extra_inputs=extra_inputs,
                ),
            )
        except (CommandError, ValueError) as exc:
            self.window.show_error(str(exc))
            return

        task = TaskRecord(operation=operation, input_path=input_path, output_path=spec.output_path)
        task.progress = None if not self._duration_seconds_for_path(input_path) else 0.0
        task.message = "Running ffmpeg"
        self.state.current_task = task
        self.task_state.add(task)
        self.task_model.append_record(task)

        self.state.logs = []
        self.window.clear_log()
        self.window.set_busy(True)
        self.window.set_progress(task.progress)
        self.window.set_current_output(None)
        self.window.set_batch_progress(0, 0)
        self._append_log("$ " + " ".join(shlex.quote(arg) for arg in spec.args))

        worker = self.task_manager.create_worker(spec, self._duration_seconds_for_path(input_path))
        worker.status_changed.connect(lambda status: self._on_task_status(task, status))
        worker.progress_changed.connect(lambda progress: self._on_task_progress(task, progress))
        worker.log_received.connect(self._append_log)
        worker.result_ready.connect(lambda result: self._on_task_result(task, result))
        worker.error_occurred.connect(lambda message: self._on_task_error(task, message))
        worker.finished.connect(lambda status: self._on_task_finished(task, worker, status))
        worker.start()

    def _start_single_stack_task(
        self,
        input_path: Path,
        stack_specs: list[tuple[Operation, dict[str, object], dict[str, Path]]],
        media_info: MediaInfo | None = None,
    ) -> None:
        try:
            spec = build_stack_command(
                ffmpeg_bin=self.window.selected_ffmpeg_bin(),
                input_path=input_path,
                output_dir=self.state.output_dir,
                stack=stack_specs,
                media_info=media_info,
            )
        except (CommandError, ValueError) as exc:
            self.window.show_error(str(exc))
            return

        task = TaskRecord(operation=stack_specs[0][0], input_path=input_path, output_path=spec.output_path)
        task.progress = None if not self._duration_seconds_for_path(input_path) else 0.0
        task.message = "Running ffmpeg"
        self.state.current_task = task
        self.task_state.add(task)
        self.task_model.append_record(task)

        self.state.logs = []
        self.window.clear_log()
        self.window.set_busy(True)
        self.window.set_progress(task.progress)
        self.window.set_current_output(None)
        self.window.set_batch_progress(0, 0)
        self._append_log("$ " + " ".join(shlex.quote(arg) for arg in spec.args))

        worker = self.task_manager.create_worker(spec, self._duration_seconds_for_path(input_path))
        worker.status_changed.connect(lambda status: self._on_task_status(task, status))
        worker.progress_changed.connect(lambda progress: self._on_task_progress(task, progress))
        worker.log_received.connect(self._append_log)
        worker.result_ready.connect(lambda result: self._on_task_result(task, result))
        worker.error_occurred.connect(lambda message: self._on_task_error(task, message))
        worker.finished.connect(lambda status: self._on_task_finished(task, worker, status))
        worker.start()

    def _start_batch_task(self, input_paths: list[Path]) -> None:
        self.state.batch_input_paths = input_paths
        self._pending_total = len(input_paths)
        self._current_batch_total = len(input_paths)
        self.state.batch_total_items = len(input_paths)
        self.state.batch_current_index = 0
        self.state.batch_cancel_requested = False
        self.state.is_batch_running = True
        self.task_manager.clear_batch_cancel_flag()
        self._batch_queue = []
        display_operation = self._batch_stack_items[0][0] if self._is_batch_stack_mode else self._batch_operation

        for input_path in input_paths:
            task = TaskRecord(operation=display_operation, input_path=input_path, status=TaskStatus.pending, message="Queued")
            self.task_state.add(task)
            self.task_model.append_record(task)
            self._batch_queue.append((task, input_path))

        self.window.set_progress(None)
        self.window.set_batch_progress(0, self._current_batch_total)
        self.window.set_current_output(None)
        self.window.set_batch_buttons(pending_count=len(self._batch_queue), running=True)
        self.window.set_busy(True)
        self.window.clear_log()
        self._start_next_batch_task()

    def _start_next_batch_task(self) -> None:
        if not self.state.is_batch_running:
            return
        if self.state.batch_cancel_requested or self.task_manager.batch_cancel_requested():
            self._mark_batch_pending(TaskStatus.cancelled, "Cancelled")
            self._finish_batch()
            return
        if not self._batch_queue:
            self._finish_batch()
            return

        record, input_path = self._batch_queue.pop(0)
        self.state.current_task = record
        self.state.batch_current_index += 1
        self.window.set_batch_progress(self.state.batch_current_index, self._current_batch_total)
        self.window.set_batch_buttons(pending_count=len(self._batch_queue), running=True)
        try:
            if self._is_batch_stack_mode:
                spec = build_stack_command(
                    ffmpeg_bin=self.window.selected_ffmpeg_bin(),
                    input_path=input_path,
                    output_dir=self.state.output_dir,
                    stack=self._batch_stack_items,
                    media_info=self.state.media_info,
                )
            else:
                spec = self.ffmpeg_service.build_command(
                    self.window.selected_ffmpeg_bin(),
                    TaskRequest(
                        input_path=input_path,
                        output_dir=self.state.output_dir,
                        operation=self._batch_operation,
                        options=self._batch_options,
                        extra_inputs=self._batch_extra_inputs,
                    ),
                )
        except (CommandError, ValueError) as exc:
            record.status = TaskStatus.failed
            record.message = str(exc)
            record.progress = 0.0
            record.touch()
            self.task_model.notify_record_changed(record)
            self.window.show_status(f"{record.input_path.name} 跳过：{exc}")
            self.state.logs = []
            self.window.clear_log()
            self._start_next_batch_task()
            return

        record.status = TaskStatus.running
        record.output_path = spec.output_path
        record.progress = None if not self._duration_seconds_for_path(input_path) else 0.0
        record.message = "Running ffmpeg"
        record.touch()
        self.task_model.notify_record_changed(record)

        self.state.logs = []
        self.window.clear_log()
        self.window.set_progress(record.progress)
        self.window.set_current_output(None)
        self._append_log(f"[{self.state.batch_current_index}/{self._current_batch_total}] " + " ".join(shlex.quote(arg) for arg in spec.args))

        worker = self.task_manager.create_worker(spec, self._duration_seconds_for_path(input_path))
        worker.status_changed.connect(lambda status: self._on_task_status(record, status))
        worker.progress_changed.connect(lambda progress: self._on_task_progress(record, progress))
        worker.log_received.connect(self._append_log)
        worker.result_ready.connect(lambda result: self._on_task_result(record, result))
        worker.error_occurred.connect(lambda message: self._on_task_error(record, message))
        worker.finished.connect(lambda status: self._on_task_finished(record, worker, status))
        worker.start()

    def _collect_input_paths(self) -> list[Path]:
        if self.state.batch_input_paths:
            return list(self.state.batch_input_paths)
        input_path = self.window.selected_input_path()
        if input_path and input_path.exists():
            return [input_path]
        return []

    def _on_probe_task_path(self, path: Path) -> bool:
        return self.state.input_path == path

    def _start_probe(self, path: Path) -> None:
        if self._probe_thread and self._probe_thread.isRunning():
            self._probe_thread.quit()
            self._probe_thread.wait(500)
        self.window.show_status("正在读取媒体信息...")
        thread = QThread()
        worker = ProbeWorker(self.ffmpeg_service, self.window.selected_ffprobe_bin(), path)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.media_info_ready.connect(lambda media_info: self._on_media_info(path, media_info))
        worker.error_occurred.connect(self.window.show_status)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_probe_worker)
        self._probe_thread = thread
        self._probe_worker = worker
        thread.start()

    def _clear_probe_worker(self) -> None:
        self._probe_thread = None
        self._probe_worker = None

    def _on_media_info(self, path: Path, media_info: MediaInfo) -> None:
        if self.state.input_path != path:
            return
        self.state.media_info = media_info
        self.window.set_media_info(media_info)
        if media_info.has_error:
            self.window.show_status(media_info.error_message or "ffprobe failed")
        else:
            self.window.show_status("媒体信息读取完成")
        self.window.set_start_enabled(self.state.can_start())

    def _on_task_status(self, task: TaskRecord, status: TaskStatus) -> None:
        task.status = status
        task.touch()
        self.task_model.notify_record_changed(task)

    def _on_task_progress(self, task: TaskRecord, progress: float | None) -> None:
        task.progress = progress
        task.touch()
        self.window.set_progress(progress)
        self.task_model.notify_record_changed(task)

    def _on_task_result(self, task: TaskRecord, result: TaskResult) -> None:
        task.output_path = result.output_path
        task.message = f"Finished: {result.output_size} bytes"
        task.touch()
        self.window.set_current_output(result.output_path)
        self.task_model.notify_record_changed(task)

    def _on_task_error(self, task: TaskRecord, message: str) -> None:
        task.status = TaskStatus.failed
        task.message = message
        task.touch()
        self._append_log("ERROR: " + message)
        self.window.show_status(message)
        self.task_model.notify_record_changed(task)

    def _on_task_finished(self, task: TaskRecord, worker, status: TaskStatus) -> None:
        task.status = status
        if status is TaskStatus.succeeded:
            task.message = task.message if task.message.startswith("Finished") else "Finished"
        elif status is TaskStatus.cancelled:
            task.message = "Cancelled"
            task.progress = 0.0
        elif status is TaskStatus.failed and not task.message:
            task.message = "Failed"
        task.touch()
        self.task_model.notify_record_changed(task)
        self.log_service.save_task_log(task, self.state.logs)
        self.task_manager.clear_current(worker)

        if self.state.is_batch_running:
            if self.state.batch_cancel_requested or self.task_manager.batch_cancel_requested():
                self._mark_batch_pending(TaskStatus.cancelled, "Cancelled")
                self._finish_batch()
                return
            if self._batch_queue:
                self._start_next_batch_task()
                return
            self._finish_batch()
            return

        self.window.set_busy(False)
        self.window.set_start_enabled(self.state.can_start())
        if status is TaskStatus.succeeded:
            self.window.show_status("任务完成")
        elif status is TaskStatus.cancelled:
            self.window.show_status("任务已取消")
        else:
            self.window.show_status(task.message)

    def _finish_batch(self) -> None:
        self.state.current_task = None
        self.state.is_batch_running = False
        self.state.batch_cancel_requested = False
        self.task_manager.clear_batch_cancel_flag()
        self._batch_queue.clear()
        self.window.set_busy(False)
        self.window.set_batch_buttons(pending_count=0, running=False)
        self.window.set_start_enabled(self.state.can_start())
        self.window.set_batch_progress(self._current_batch_total, self._current_batch_total)
        self.window.set_progress(0.0)

    def _mark_batch_pending(self, status: TaskStatus, message: str) -> None:
        for record, _ in self._batch_queue:
            record.status = status
            record.message = message
            record.touch()
            self.task_model.notify_record_changed(record)

    def _remove_pending_records(self, records: list[TaskRecord]) -> None:
        pending_ids = {record.task_id for record in records}
        self.task_model.remove_records(pending_ids)

    def _append_log(self, line: str) -> None:
        self.state.logs.append(line)
        self.window.append_log(line)

    def _duration_seconds_for_path(self, input_path: Path) -> float | None:
        if self.state.input_path == input_path and self.state.media_info:
            return self.state.media_info.duration_seconds
        return None

    def _validate_operation_inputs(self, operation: Operation, extra_inputs: dict[str, Path]) -> None:
        if operation is not Operation.subtitles:
            return
        subtitle_path = extra_inputs.get("subtitle")
        if not subtitle_path:
            raise ValueError("请选择字幕文件")
        if not subtitle_path.exists():
            raise ValueError("字幕文件不存在")
        if subtitle_path.suffix.lower() not in SUBTITLE_EXTENSIONS:
            raise ValueError("字幕文件只支持 .srt/.vtt/.ass/.ssa")

    def _save_current_config(self) -> None:
        output_dir = self.window.selected_output_dir() or self.output_service.default_output_dir()
        config = AppConfig(
            ffmpeg_bin=self.window.selected_ffmpeg_bin(),
            ffprobe_bin=self.window.selected_ffprobe_bin(),
            output_dir=output_dir,
        )
        self.config_service.save(config)
