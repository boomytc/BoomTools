from __future__ import annotations

import json
import shlex
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Slot

from desktop.app.core.config import AppConfig
from desktop.app.runtime.binaries import RuntimeHealth, runtime_health_snapshot
from desktop.app.runtime.ffmpeg import CommandError, CommandSpec
from desktop.app.runtime.filter_chain import build_stack_command, validate_crop_media_context
from desktop.app.services.config_service import ConfigService
from desktop.app.services.ffmpeg_service import FfmpegService
from desktop.app.services.log_service import LogService
from desktop.app.services.output_service import OutputService
from desktop.app.services.sleep_inhibitor import SleepInhibitionResult, SleepInhibitor
from desktop.app.tasks.health_worker import HealthWorker
from desktop.app.tasks.probe_worker import ProbeWorker
from desktop.app.tasks.task_manager import TaskManager
from desktop.app.tasks.zip_results_worker import ZipResultsWorker
from desktop.app.ui.main_window import MainWindow
from desktop.app.ui.widgets.task_table_model import TaskTableModel
from desktop.app.viewmodels.app_state import AppState, RecentBatchState
from desktop.app.viewmodels.task_state import TaskState
from shared.contracts import (
    BATCH_SUPPORTED_OPERATIONS,
    MediaInfo,
    Operation,
    STACK_FILTER_OPERATIONS,
    STACK_MAX_ITEMS,
    TaskRecord,
    TaskRequest,
    TaskResult,
    TaskStatus,
    operation_label,
    operation_short_label,
)


SUBTITLE_EXTENSIONS = {".srt", ".vtt", ".ass", ".ssa"}


class MainController(QObject):
    def __init__(
        self,
        window: MainWindow,
        task_model: TaskTableModel,
        *,
        config_service: ConfigService,
        ffmpeg_service: FfmpegService,
        output_service: OutputService,
        log_service: LogService,
        sleep_inhibitor: SleepInhibitor,
        task_manager: TaskManager,
    ) -> None:
        super().__init__()
        self.window = window
        self.task_model = task_model
        self.config_service = config_service
        self.ffmpeg_service = ffmpeg_service
        self.output_service = output_service
        self.log_service = log_service
        self.sleep_inhibitor = sleep_inhibitor
        self.task_manager = task_manager

        self.state = AppState()
        self.task_state = TaskState()
        self._health_thread: QThread | None = None
        self._health_worker: HealthWorker | None = None
        self._probe_thread: QThread | None = None
        self._probe_worker: ProbeWorker | None = None
        self._probe_context: str | None = None
        self._batch_probe_record: TaskRecord | None = None
        self._batch_probe_error: str | None = None
        self._selection_probe_queue: list[TaskRecord] = []
        self._selection_probe_record: TaskRecord | None = None
        self._selection_probe_error: str | None = None
        self._zip_thread: QThread | None = None
        self._zip_worker: ZipResultsWorker | None = None
        self._zip_running = False

        self._batch_queue: list[tuple[TaskRecord, Path]] = []
        self._batch_operation: Operation = Operation.convert
        self._batch_options: dict[str, object] = {}
        self._batch_extra_inputs: dict[str, Path] = {}
        self._batch_stack_items: list[tuple[Operation, dict[str, object], dict[str, Path]]] = []
        self._batch_records: list[TaskRecord] = []
        self._is_batch_stack_mode: bool = False
        self._pending_total: int = 0
        self._current_batch_total: int = 0
        self._stack_items: list[tuple[Operation, dict[str, object], dict[str, Path]]] = []
        self._prepared_records: list[TaskRecord] = []
        self._media_info_cache: dict[Path, MediaInfo] = {}

        self._connect_signals()

    def initialize(self) -> None:
        config = self.config_service.load()
        output_dir = self.output_service.normalize_output_dir(config.output_dir)
        self.window.set_initial_paths(
            ffmpeg_bin=config.ffmpeg_bin,
            ffprobe_bin=config.ffprobe_bin,
            output_dir=output_dir,
            prevent_sleep_during_tasks=config.prevent_sleep_during_tasks,
        )
        self.state.output_dir = output_dir
        self.state.prevent_sleep_during_tasks = config.prevent_sleep_during_tasks
        self.sleep_inhibitor.set_enabled(config.prevent_sleep_during_tasks)
        self.refresh_runtime_health()
        self.window.set_batch_progress(0, 0)
        self.window.set_stack_items([])
        self.window.set_stack_mode(False)
        self.window.set_batch_input_mode(False)
        self.window.set_start_enabled(self.state.can_start())
        self.window.set_batch_buttons(pending_count=0, running=False)
        self.window.set_zip_results_enabled(False)
        self._refresh_recent_batch_results_state()

    def refresh_runtime_health(self, *, include_version: bool = True) -> None:
        self._save_current_config()
        ffmpeg_bin = self.window.selected_ffmpeg_bin()
        ffprobe_bin = self.window.selected_ffprobe_bin()
        self._stop_health_thread()
        self._apply_runtime_health(runtime_health_snapshot(ffmpeg_bin, ffprobe_bin))
        if include_version:
            self._start_health_thread(ffmpeg_bin, ffprobe_bin)

    def on_input_file_selected(self, path_text: str) -> None:
        self.on_batch_files_selected([path_text])

    def on_batch_files_selected(self, path_texts: list[str]) -> None:
        batch_paths = [Path(path) for path in path_texts if Path(path).exists()]
        if not batch_paths:
            self.window.show_error("请选择至少一个可用文件")
            return
        added_records = self._append_prepared_inputs(batch_paths, status=TaskStatus.ready, message="已添加到任务队列")
        input_paths = self._prepared_input_paths()
        self._sync_input_state(input_paths)
        self.state.media_info = self._media_info_for_path(self.state.input_path) if self.state.input_path else None
        self.window.set_media_info(self.state.media_info)
        self.window.reset_progress()
        self.window.set_current_output(None)
        self.window.set_batch_progress(0, len(input_paths))
        self._queue_selection_probes(added_records)
        self._refresh_start_state()
        self._refresh_command_preview()

    def on_input_mode_changed(self, batch_mode: bool) -> None:
        self.state.input_mode = "batch" if batch_mode else "single"
        self.window.set_batch_input_mode(batch_mode)
        if batch_mode:
            selected_batch_paths = [path for path in self.window.selected_batch_paths() if path.exists()]
            self.state.batch_input_paths = selected_batch_paths
            if selected_batch_paths:
                self.state.input_path = selected_batch_paths[0]
                self.state.media_info = self._media_info_for_path(self.state.input_path)
                self.window.set_media_info(self.state.media_info)
                self.window.set_batch_progress(0, len(selected_batch_paths))
                self._set_prepared_inputs(selected_batch_paths, status=TaskStatus.ready, message="已选择")
                self._queue_selection_probes(self._prepared_records)
            else:
                self._clear_prepared_records()
                self.window.set_batch_progress(0, 0)
        else:
            self.state.input_path = self.window.selected_input_path()
            if self.state.input_path and self.state.input_path.exists():
                self._set_prepared_inputs([self.state.input_path], status=TaskStatus.ready, message="已选择")
                self._queue_selection_probes(self._prepared_records)
            else:
                self._clear_prepared_records()
        self._refresh_start_state()
        self._refresh_command_preview()

    def on_batch_files_cleared(self) -> None:
        self.state.batch_input_paths = []
        if self.state.input_mode == "batch":
            self.state.input_path = None
        self._clear_prepared_records()
        self._cancel_selection_probes()
        self.window.set_batch_progress(0, 0)
        self._refresh_start_state()
        self._refresh_command_preview()

    def on_output_dir_selected(self, path_text: str) -> None:
        path = self.output_service.normalize_output_dir(Path(path_text))
        self.state.output_dir = path
        self._save_current_config()

    def start_task(self) -> None:
        self.refresh_runtime_health(include_version=False)
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
        if not input_paths:
            self.window.show_error("请先选择存在的本机媒体文件")
            return
        if use_stack and not stack_specs:
            self.window.show_error("Stack 需要至少添加一个可链式操作")
            return
        self._cancel_selection_probes()

        if len(input_paths) > 1:
            if use_stack:
                unsupported_operation = _unsupported_batch_stack_operation(stack_specs)
                if unsupported_operation is not None:
                    self.window.show_error(f"Stack 批处理暂不支持「{operation_label(unsupported_operation)}」")
                    return
            elif operation not in BATCH_SUPPORTED_OPERATIONS:
                self.window.show_error("该操作不支持批处理")
                return

        try:
            self._validate_duration_requirements(stack_specs, input_paths)
        except ValueError as exc:
            self.window.show_error(str(exc))
            return

        if not use_stack and operation is Operation.media_info:
            self._complete_media_info_task(input_paths[0])
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
        self._start_batch_task(input_paths)

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

    def remove_task(self, task_id: str) -> None:
        record = self._task_record_by_id(task_id)
        if record is None:
            return
        if record.status in {TaskStatus.probing, TaskStatus.running}:
            self.window.show_status("运行中或读取中的任务不可移除，请先取消")
            return

        was_prepared = any(prepared.task_id == task_id for prepared in self._prepared_records)
        self._prepared_records = [prepared for prepared in self._prepared_records if prepared.task_id != task_id]
        self._selection_probe_queue = [record for record in self._selection_probe_queue if record.task_id != task_id]

        previous_queue_count = len(self._batch_queue)
        self._batch_queue = [(queued_record, path) for queued_record, path in self._batch_queue if queued_record.task_id != task_id]
        was_queued = len(self._batch_queue) != previous_queue_count

        self.task_model.remove_records({task_id})
        self.task_state.remove_records({task_id})
        if self.state.current_task and self.state.current_task.task_id == task_id:
            self.state.current_task = None
            self.window.set_current_output(None)

        if was_prepared:
            input_paths = self._prepared_input_paths()
            self._sync_input_state(input_paths)
            self.state.media_info = None
            self.window.set_media_info(None)
            self.window.set_batch_progress(0, len(input_paths))
            self._refresh_start_state()
            self._refresh_command_preview()

        if was_queued and self.state.is_batch_running:
            self._current_batch_total = self.state.batch_current_index + len(self._batch_queue)
            self.state.batch_total_items = self._current_batch_total
            self.window.set_batch_progress(self.state.batch_current_index, self._current_batch_total)
            self.window.set_batch_buttons(pending_count=len(self._batch_queue), running=True)

        self.window.show_status("已从任务队列移除任务")
        self._refresh_recent_batch_results_state()

    def open_output(self) -> None:
        self.window.open_output()

    def open_output_dir(self) -> None:
        self.window.open_output_dir()

    def zip_batch_outputs(self) -> None:
        if self._zip_running:
            self.window.show_status("正在打包成功结果，请稍候")
            return
        records = self._last_batch_records()
        if not records:
            self.window.show_status("当前没有可打包的批量结果")
            return
        if not self._successful_recent_batch_outputs():
            self.window.show_status("最近批次没有可打包的成功输出")
            return

        output_dir = self.state.output_dir or self.output_service.default_output_dir()
        self._start_zip_thread(records, output_dir)

    def copy_recent_batch_output_paths(self) -> None:
        output_paths = self._successful_recent_batch_outputs()
        if not output_paths:
            self.window.show_status("最近批次没有可复制的成功输出路径")
            return
        self.window.copy_text_to_clipboard("\n".join(str(path) for path in output_paths))
        self.window.show_status(f"已复制 {len(output_paths)} 个成功输出路径")

    def open_recent_batch_output_dir(self) -> None:
        if not self._last_batch_records():
            self.window.show_status("当前没有最近批次输出目录")
            return
        output_dir = self._recent_batch_output_dir()
        if output_dir is None:
            self.window.show_status("当前没有最近批次输出目录")
            return
        if not output_dir.exists():
            self.window.show_status(f"最近批次输出目录不存在：{output_dir}")
            return
        self.window.open_directory(output_dir)
        self.window.show_status(f"已打开最近批次输出目录：{output_dir}")

    def locate_recent_batch_results(self) -> None:
        task_ids = set(self.state.recent_batch.task_ids)
        if not task_ids:
            self.window.show_status("当前没有最近批次可定位")
            return
        selected_count = self.window.select_task_ids(task_ids)
        if selected_count == 0:
            self.window.show_status("任务表中没有最近批次结果")
            return
        self.window.show_status(f"已定位最近批次 {selected_count} 条结果")

    def close(self) -> None:
        self.cancel_current_task()
        self.cancel_batch()
        self.task_manager.cancel_current(preserve_batch_cancel=True, wait=True)
        self._cancel_selection_probes()
        self._stop_health_thread()
        self._stop_probe_thread()
        self._stop_zip_thread()
        self._stop_sleep_inhibition()

    def copy_output_path(self) -> None:
        current_output = self.window.current_output_path()
        if not current_output:
            self.window.show_status("当前无可复制的输出路径")
            return
        self.window.copy_output_path()

    def _connect_signals(self) -> None:
        self.window.input_file_selected.connect(self.on_input_file_selected)
        self.window.input_mode_changed.connect(self.on_input_mode_changed)
        self.window.batch_files_selected.connect(self.on_batch_files_selected)
        self.window.batch_files_cleared.connect(self.on_batch_files_cleared)
        self.window.output_dir_selected.connect(self.on_output_dir_selected)
        self.window.refresh_requested.connect(self.refresh_runtime_health)
        self.window.start_requested.connect(self.start_task)
        self.window.cancel_requested.connect(self.cancel_current_task)
        self.window.cancel_queue_requested.connect(self.cancel_batch)
        self.window.remove_pending_requested.connect(self.remove_pending_batch_tasks)
        self.window.task_remove_requested.connect(self.remove_task)
        self.window.stack_mode_toggled.connect(self._on_stack_mode_toggled)
        self.window.stack_add_requested.connect(self._on_stack_add_requested)
        self.window.stack_remove_requested.connect(self._on_stack_remove_requested)
        self.window.stack_clear_requested.connect(self._on_stack_clear_requested)
        self.window.stack_item_selected.connect(self._on_stack_item_selected)
        self.window.stack_item_moved.connect(self._on_stack_item_moved)
        self.window.command_preview_requested.connect(self._refresh_command_preview)
        self.window.open_output_requested.connect(self.open_output)
        self.window.open_output_dir_requested.connect(self.open_output_dir)
        self.window.zip_outputs_requested.connect(self.zip_batch_outputs)
        self.window.copy_batch_output_paths_requested.connect(self.copy_recent_batch_output_paths)
        self.window.open_batch_output_dir_requested.connect(self.open_recent_batch_output_dir)
        self.window.locate_batch_results_requested.connect(self.locate_recent_batch_results)
        self.window.copy_output_path_requested.connect(self.copy_output_path)
        self.window.closing.connect(self.close)

    def _on_stack_mode_toggled(self, enabled: bool) -> None:
        self.window.set_stack_mode(enabled)
        self._refresh_stack_buttons()
        self._refresh_start_state()
        self._refresh_command_preview()

    def _refresh_stack_buttons(self) -> None:
        self.window.refresh_stack_controls()
        self.window.set_stack_items([self._format_stack_item(item) for item in self._stack_items])

    def _on_stack_add_requested(self) -> None:
        operation, options, extra_inputs = self.window.selected_operation_payload()
        if operation not in STACK_FILTER_OPERATIONS:
            self.window.show_error("当前动作不支持加入 Stack")
            return
        if len(self._stack_items) >= STACK_MAX_ITEMS:
            return
        try:
            self._validate_operation_inputs(operation, extra_inputs)
        except ValueError as exc:
            self.window.show_error(str(exc))
            return
        options = dict(options)
        extra_inputs = dict(extra_inputs)
        if self._stack_items:
            options.pop("start_seconds", None)
            options.pop("end_seconds", None)

        self._stack_items.append((operation, options, extra_inputs))
        self.window.set_stack_items([self._format_stack_item(item) for item in self._stack_items])
        self._sync_stack_payload(len(self._stack_items) - 1)
        self._refresh_command_preview()

    def _on_stack_item_moved(self, from_index: int, to_index: int) -> None:
        if from_index < 0 or from_index >= len(self._stack_items):
            return
        if to_index < 0 or to_index >= len(self._stack_items):
            return
        if from_index == to_index:
            self._sync_stack_payload(to_index)
            return
        item = self._stack_items.pop(from_index)
        self._stack_items.insert(to_index, item)
        self.window.set_stack_items([self._format_stack_item(item) for item in self._stack_items])
        self._sync_stack_payload(to_index)
        self._refresh_start_state()
        self._refresh_command_preview()

    def _on_stack_remove_requested(self, index: int) -> None:
        if index < 0 or index >= len(self._stack_items):
            return
        self._stack_items.pop(index)
        self.window.set_stack_items([self._format_stack_item(item) for item in self._stack_items])
        if self._stack_items:
            self._sync_stack_payload(min(index, len(self._stack_items) - 1))
        self._refresh_command_preview()

    def _on_stack_clear_requested(self) -> None:
        self._stack_items = []
        self.window.set_stack_items([])
        self._refresh_command_preview()

    def _on_stack_item_selected(self, index: int) -> None:
        self._sync_stack_payload(index)
        self._refresh_start_state()
        self._refresh_command_preview()

    def _sync_stack_payload(self, index: int) -> None:
        if index < 0 or index >= len(self._stack_items):
            return
        operation, options, extra_inputs = self._stack_items[index]
        self.window.set_operation_payload(operation, dict(options), dict(extra_inputs))

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
                batch_error = f"多个文件暂不支持「{operation_label(operation)}」。"
        if self.window.stack_mode():
            try:
                stack_specs = self._collect_stack_specs(*self.window.selected_operation_payload())
                can_stack = bool(stack_specs)
            except (ValueError, OSError, CommandError):
                stack_specs = []
                can_stack = False
            can_start = can_start and can_stack
            batch_error = None
            if can_stack and len(input_paths) > 1:
                unsupported_operation = _unsupported_batch_stack_operation(stack_specs)
                if unsupported_operation is not None:
                    can_start = False
                    batch_error = f"Stack 批处理暂不支持「{operation_label(unsupported_operation)}」。"

        if batch_error:
            self.window.show_status(batch_error)
        self.window.set_start_enabled(can_start)

    def _refresh_command_preview(self) -> None:
        try:
            operation, options, extra_inputs = self.window.selected_operation_payload()
            self._refresh_prepared_operation()
            if operation is Operation.media_info:
                args = [
                    self.window.selected_ffprobe_bin(),
                    "-v",
                    "error",
                    "-print_format",
                    "json",
                    "-show_format",
                    "-show_streams",
                    "input_placeholder",
                ]
                self.window.set_command_preview("$ " + " ".join(shlex.quote(arg) for arg in args))
                self.window.set_output_estimate("输出大小保守估算：此操作只展示媒体信息，不生成文件")
                return
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
                    validate_capabilities=False,
                )
        except (CommandError, ValueError, OSError) as exc:
            self.window.set_command_preview(f"预览失败：{exc}")
            self.window.set_output_estimate("输出大小保守估算：参数异常，无法估算")
            return

        self.window.set_command_preview(_format_command_preview(spec))
        self.window.set_output_estimate(self._format_output_estimate(spec))

    def _format_output_estimate(self, spec: CommandSpec) -> str:
        if spec.output_path is None:
            return "输出大小保守估算：此命令不生成文件"
        if len(self._collect_input_paths()) > 1:
            return "输出大小保守估算：多个文件会按每个文件实际时长生成"
        if not self.state.media_info or not self.state.media_info.duration_seconds:
            return "输出大小保守估算：等待媒体时长后估算"

        bitrate = self._estimate_bitrate(spec.output_path.suffix)
        if bitrate is None:
            return "输出大小保守估算：当前格式不支持估算"
        size_bytes = int(self.state.media_info.duration_seconds * bitrate / 8)
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
        operation, _options, _ = item
        return operation_short_label(operation)

    def _set_prepared_inputs(self, input_paths: list[Path], *, status: TaskStatus, message: str) -> None:
        self._clear_prepared_records()
        self._append_prepared_inputs(input_paths, status=status, message=message)

    def _append_prepared_inputs(self, input_paths: list[Path], *, status: TaskStatus, message: str) -> list[TaskRecord]:
        operation, operation_text = self._queue_operation_display()
        existing_paths = {record.input_path for record in self._prepared_records}
        added_records: list[TaskRecord] = []
        for input_path in input_paths:
            if input_path in existing_paths:
                continue
            record = TaskRecord(
                operation=operation,
                operation_text=operation_text,
                input_path=input_path,
                status=status,
                message=message,
                progress=0.0,
            )
            self._prepared_records.append(record)
            added_records.append(record)
            existing_paths.add(input_path)
            self.task_state.add(record)
            self.task_model.append_record(record)
        return added_records

    def _clear_prepared_records(self) -> None:
        self._cancel_selection_probes()
        if not self._prepared_records:
            return
        task_ids = {record.task_id for record in self._prepared_records}
        self.task_model.remove_records(task_ids)
        self.task_state.remove_records(task_ids)
        self._prepared_records.clear()

    def _queue_selection_probes(self, records: list[TaskRecord]) -> None:
        if self.state.is_batch_running:
            return
        for record in records:
            if record.input_path in self._media_info_cache:
                media_info = self._media_info_cache[record.input_path]
                self._apply_selection_media_info(record, media_info, show_status=False)
                continue
            if record is self._selection_probe_record:
                continue
            if any(queued.task_id == record.task_id for queued in self._selection_probe_queue):
                continue
            if record.status in {TaskStatus.running, TaskStatus.succeeded, TaskStatus.failed, TaskStatus.cancelled}:
                continue
            self._selection_probe_queue.append(record)
        self._start_next_selection_probe()

    def _start_next_selection_probe(self) -> None:
        if self.state.is_batch_running:
            return
        if self._selection_probe_record is not None:
            return
        if self._probe_thread and self._probe_thread.isRunning():
            return
        if not self._selection_probe_supported():
            return
        while self._selection_probe_queue:
            record = self._selection_probe_queue.pop(0)
            if record not in self._prepared_records:
                continue
            if not record.input_path.exists():
                continue
            cached = self._media_info_cache.get(record.input_path)
            if cached is not None:
                self._apply_selection_media_info(record, cached, show_status=False)
                continue
            self._selection_probe_record = record
            record.status = TaskStatus.probing
            record.message = "正在读取媒体信息"
            record.progress = None
            record.touch()
            self.task_model.notify_record_changed(record)
            self._start_probe(record.input_path, context="selection", selection_record=record)
            return

    def _selection_probe_supported(self) -> bool:
        health = self.state.runtime_health
        return bool(health and health.ffprobe_available)

    def _cancel_selection_probes(self) -> None:
        self._selection_probe_queue.clear()
        record = self._selection_probe_record
        self._selection_probe_record = None
        self._selection_probe_error = None
        if self._probe_context == "selection":
            self._stop_probe_thread()
        if record is None:
            return
        if record.status is TaskStatus.probing:
            record.status = TaskStatus.ready
            record.message = "已添加到任务队列"
            record.progress = 0.0
            record.touch()
            self.task_model.notify_record_changed(record)

    def _task_record_by_id(self, task_id: str) -> TaskRecord | None:
        for record in self.task_model.records():
            if record.task_id == task_id:
                return record
        return None

    def _queue_operation_display(self) -> tuple[Operation, str | None]:
        selected_operation = self.window.selected_operation()
        if not self.window.stack_mode():
            return selected_operation, None
        if self._stack_items:
            return self._stack_items[0][0], f"Stack x{len(self._stack_items)}"
        return selected_operation, "Stack"

    def _refresh_prepared_operation(self) -> None:
        if not self._prepared_records:
            return
        operation, operation_text = self._queue_operation_display()
        for record in self._prepared_records:
            record.operation = operation
            record.operation_text = operation_text
            record.touch()
            self.task_model.notify_record_changed(record)

    def _start_record_for_path(
        self,
        input_path: Path,
        *,
        operation: Operation,
        operation_text: str | None,
        output_path: Path | None,
        status: TaskStatus,
        message: str,
        progress: float | None,
    ) -> TaskRecord:
        record = self._pop_prepared_record(input_path)
        if record is None:
            record = TaskRecord(operation=operation, operation_text=operation_text, input_path=input_path)
            self.task_state.add(record)
            self.task_model.append_record(record)
        record.operation = operation
        record.operation_text = operation_text
        record.output_path = output_path
        record.status = status
        record.message = message
        record.progress = progress
        record.touch()
        self.task_model.notify_record_changed(record)
        return record

    def _pop_prepared_record(self, input_path: Path) -> TaskRecord | None:
        for index, record in enumerate(self._prepared_records):
            if record.input_path == input_path:
                return self._prepared_records.pop(index)
        return None

    def _prepared_record_for_path(self, input_path: Path) -> TaskRecord | None:
        for record in self._prepared_records:
            if record.input_path == input_path:
                return record
        return None

    def _start_single_task(
        self,
        operation: Operation,
        options: dict[str, object],
        extra_inputs: dict[str, Path],
        input_path: Path,
    ) -> None:
        try:
            options = self._options_with_media_duration(operation, options, input_path)
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

        task = self._start_record_for_path(
            input_path,
            operation=operation,
            operation_text=None,
            output_path=spec.output_path,
            status=TaskStatus.running,
            message="Running ffmpeg",
            progress=None if not self._duration_seconds_for_path(input_path) else 0.0,
        )
        self.state.current_task = task

        self.state.logs = []
        self.window.clear_log()
        self.window.set_busy(True)
        self._start_sleep_inhibition()
        self.window.set_progress(task.progress)
        self.window.set_current_output(None)
        self.window.set_batch_progress(0, 0)
        for line in _format_command_lines(spec):
            self._append_log(line)

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

        task = self._start_record_for_path(
            input_path,
            operation=stack_specs[0][0],
            operation_text=f"Stack x{len(stack_specs)}",
            output_path=spec.output_path,
            status=TaskStatus.running,
            message="Running ffmpeg",
            progress=None if not self._duration_seconds_for_path(input_path) else 0.0,
        )
        self.state.current_task = task

        self.state.logs = []
        self.window.clear_log()
        self.window.set_busy(True)
        self._start_sleep_inhibition()
        self.window.set_progress(task.progress)
        self.window.set_current_output(None)
        self.window.set_batch_progress(0, 0)
        for line in _format_command_lines(spec):
            self._append_log(line)

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
        self._batch_records = []
        self.state.recent_batch = RecentBatchState()
        self._refresh_recent_batch_results_state()
        display_operation = self._batch_stack_items[0][0] if self._is_batch_stack_mode else self._batch_operation
        operation_text = f"Stack x{len(self._batch_stack_items)}" if self._is_batch_stack_mode else None

        for input_path in input_paths:
            task = self._start_record_for_path(
                input_path,
                operation=display_operation,
                operation_text=operation_text,
                output_path=None,
                status=TaskStatus.pending,
                message="Queued",
                progress=0.0,
            )
            self._batch_queue.append((task, input_path))
            self._batch_records.append(task)

        self.state.recent_batch.task_ids = {record.task_id for record in self._batch_records}
        self._refresh_recent_batch_results_state()

        self.window.set_progress(None)
        self.window.set_batch_progress(0, self._current_batch_total)
        self.window.set_current_output(None)
        self.window.set_batch_buttons(pending_count=len(self._batch_queue), running=True)
        self.window.set_busy(True)
        self._start_sleep_inhibition()
        self.window.clear_log()
        self._start_next_batch_task()

    def _start_next_batch_task(self) -> None:
        if not self.state.is_batch_running:
            return
        if self.state.batch_cancel_requested or self.task_manager.batch_cancel_requested():
            self._mark_batch_pending(TaskStatus.cancelled, "Cancelled")
            self._finish_batch(TaskStatus.cancelled)
            return
        if not self._batch_queue:
            self._finish_batch()
            return

        record, input_path = self._batch_queue.pop(0)
        self.state.current_task = record
        self.state.batch_current_index += 1
        self.window.set_batch_progress(self.state.batch_current_index, self._current_batch_total)
        self.window.set_batch_buttons(pending_count=len(self._batch_queue), running=True)
        media_info = self._media_info_for_path(input_path)
        if self._batch_needs_media_context() and media_info is None:
            self._start_batch_probe(record, input_path)
            return
        if self._batch_needs_media_context() and media_info and media_info.has_error:
            self._fail_batch_record(record, media_info.error_message or "媒体信息读取失败")
            self._start_next_batch_task()
            return

        self._start_batch_record(record, input_path)

    def _start_batch_record(self, record: TaskRecord, input_path: Path) -> None:
        try:
            if self._is_batch_stack_mode:
                stack_items = self._stack_specs_with_media_duration(self._batch_stack_items, input_path)
                spec = build_stack_command(
                    ffmpeg_bin=self.window.selected_ffmpeg_bin(),
                    input_path=input_path,
                    output_dir=self.state.output_dir,
                    stack=stack_items,
                    media_info=self._media_info_for_path(input_path),
                )
            else:
                options = self._options_with_media_duration(self._batch_operation, self._batch_options, input_path)
                if self._batch_operation is Operation.crop:
                    media_info = self._media_info_for_path(input_path)
                    if media_info is None:
                        raise ValueError("裁剪需要先读取媒体分辨率，请稍后重试。")
                    validate_crop_media_context(options=options, media_info=media_info, input_path=input_path)
                spec = self.ffmpeg_service.build_command(
                    self.window.selected_ffmpeg_bin(),
                    TaskRequest(
                        input_path=input_path,
                        output_dir=self.state.output_dir,
                        operation=self._batch_operation,
                        options=options,
                        extra_inputs=self._batch_extra_inputs,
                    ),
                )
        except (CommandError, ValueError) as exc:
            self._fail_batch_record(record, str(exc))
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
        for line in _format_command_lines(spec):
            self._append_log(f"[{self.state.batch_current_index}/{self._current_batch_total}] {line}")

        worker = self.task_manager.create_worker(spec, self._duration_seconds_for_path(input_path))
        worker.status_changed.connect(lambda status: self._on_task_status(record, status))
        worker.progress_changed.connect(lambda progress: self._on_task_progress(record, progress))
        worker.log_received.connect(self._append_log)
        worker.result_ready.connect(lambda result: self._on_task_result(record, result))
        worker.error_occurred.connect(lambda message: self._on_task_error(record, message))
        worker.finished.connect(lambda status: self._on_task_finished(record, worker, status))
        worker.start()

    def _start_batch_probe(self, record: TaskRecord, input_path: Path) -> None:
        record.status = TaskStatus.probing
        record.message = "正在读取媒体信息"
        record.progress = None
        record.touch()
        self.task_model.notify_record_changed(record)
        self.state.logs = []
        self.window.clear_log()
        self.window.set_progress(None)
        self.window.set_current_output(None)
        self._start_probe(input_path, context="batch", batch_record=record)

    def _batch_needs_media_context(self) -> bool:
        if self._is_batch_stack_mode:
            return any(_operation_needs_media_context(operation, options) for operation, options, _ in self._batch_stack_items)
        return _operation_needs_media_context(self._batch_operation, self._batch_options)

    def _stack_specs_with_media_duration(
        self,
        stack_specs: list[tuple[Operation, dict[str, object], dict[str, Path]]],
        input_path: Path,
    ) -> list[tuple[Operation, dict[str, object], dict[str, Path]]]:
        adjusted_specs: list[tuple[Operation, dict[str, object], dict[str, Path]]] = []
        for operation, options, extra_inputs in stack_specs:
            adjusted_specs.append((operation, self._options_with_media_duration(operation, options, input_path), extra_inputs))
        return adjusted_specs

    def _fail_batch_record(self, record: TaskRecord, message: str) -> None:
        record.status = TaskStatus.failed
        record.message = message
        record.progress = 0.0
        record.touch()
        self.task_model.notify_record_changed(record)

    def _collect_input_paths(self) -> list[Path]:
        prepared_paths = self._prepared_input_paths()
        if prepared_paths:
            return prepared_paths
        if self.state.input_mode == "batch":
            if self.state.batch_input_paths:
                return list(self.state.batch_input_paths)
            return [path for path in self.window.selected_batch_paths() if path.exists()]
        input_path = self.window.selected_input_path()
        if input_path and input_path.exists():
            return [input_path]
        return []

    def _prepared_input_paths(self) -> list[Path]:
        return [record.input_path for record in self._prepared_records if record.input_path.exists()]

    def _sync_input_state(self, input_paths: list[Path]) -> None:
        self.state.input_mode = "batch" if len(input_paths) > 1 else "single"
        self.state.input_path = input_paths[0] if input_paths else None
        self.state.batch_input_paths = list(input_paths) if len(input_paths) > 1 else []
        self.window.set_batch_input_mode(len(input_paths) > 1)
        self.window.set_batch_input_paths(input_paths)

    def _start_health_thread(self, ffmpeg_bin: str, ffprobe_bin: str) -> None:
        thread = QThread()
        worker = HealthWorker(ffmpeg_bin, ffprobe_bin)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.health_ready.connect(self._on_runtime_health_ready)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(
            lambda health_thread=thread, health_worker=worker: self._clear_health_worker(
                health_thread,
                health_worker,
            )
        )
        self._health_thread = thread
        self._health_worker = worker
        thread.start()

    def _stop_health_thread(self, wait_msecs: int = 1500) -> None:
        thread = self._health_thread
        worker = self._health_worker
        if not thread:
            return
        if worker is not None:
            worker.cancel()
        if thread.isRunning():
            thread.quit()
            thread.wait(wait_msecs)

    def _clear_health_worker(self, thread: QThread, worker: HealthWorker) -> None:
        if self._health_thread is not thread or self._health_worker is not worker:
            return
        self._health_thread = None
        self._health_worker = None

    @Slot(str, str, object)
    def _on_runtime_health_ready(self, ffmpeg_bin: str, ffprobe_bin: str, health: RuntimeHealth) -> None:
        if ffmpeg_bin != self.window.selected_ffmpeg_bin() or ffprobe_bin != self.window.selected_ffprobe_bin():
            return
        self._apply_runtime_health(health)

    def _apply_runtime_health(self, health: RuntimeHealth) -> None:
        self.state.runtime_health = health
        self.window.set_runtime_health(health)
        self.window.set_start_enabled(self.state.can_start())
        if self.state.is_batch_running:
            self.window.set_batch_buttons(
                pending_count=len(self._batch_queue),
                running=health.ok
                and self.state.current_task is not None
                and self.state.current_task.status is TaskStatus.running,
            )

    def _on_probe_task_path(self, path: Path) -> bool:
        return self.state.input_path == path

    def _start_probe(
        self,
        path: Path,
        *,
        context: str = "direct",
        batch_record: TaskRecord | None = None,
        selection_record: TaskRecord | None = None,
    ) -> None:
        if self._probe_thread and self._probe_thread.isRunning():
            self._stop_probe_thread()
        self._probe_context = context
        self._batch_probe_record = batch_record
        self._batch_probe_error = None
        self._selection_probe_record = selection_record
        self._selection_probe_error = None
        if context in {"batch", "selection"}:
            self.window.show_status(f"{path.name}：正在读取媒体信息...")
        else:
            self.window.show_status("正在读取媒体信息...")
        thread = QThread()
        worker = ProbeWorker(self.ffmpeg_service, self.window.selected_ffprobe_bin(), path)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.media_info_ready.connect(self._on_media_info)
        worker.error_occurred.connect(self._on_probe_error)
        worker.finished.connect(self._on_probe_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(
            lambda probe_thread=thread, probe_worker=worker: self._clear_probe_worker(
                probe_thread,
                probe_worker,
            )
        )
        self._probe_thread = thread
        self._probe_worker = worker
        thread.start()

    def _stop_probe_thread(self, wait_msecs: int = 1500) -> None:
        thread = self._probe_thread
        worker = self._probe_worker
        if not thread:
            return
        if worker is not None:
            worker.cancel()
        if thread.isRunning():
            thread.quit()
            thread.wait(wait_msecs)

    def _start_zip_thread(self, records: list[TaskRecord], output_dir: Path) -> None:
        self._stop_zip_thread()
        thread = QThread()
        worker = ZipResultsWorker(self.output_service, records, output_dir)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.result_ready.connect(self._on_zip_results_ready)
        worker.error_occurred.connect(self._on_zip_results_error)
        worker.finished.connect(self._on_zip_results_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda zip_thread=thread, zip_worker=worker: self._clear_zip_worker(zip_thread, zip_worker))
        self._zip_thread = thread
        self._zip_worker = worker
        self._zip_running = True
        self.window.set_zip_results_enabled(False, running=True)
        self.window.show_status("正在打包成功结果...")
        self._start_sleep_inhibition()
        thread.start()

    def _stop_zip_thread(self, wait_msecs: int = 1500) -> None:
        thread = self._zip_thread
        worker = self._zip_worker
        if not thread:
            return
        if worker is not None:
            worker.cancel()
        if thread.isRunning():
            thread.quit()
            thread.wait(wait_msecs)
        self._stop_sleep_inhibition()

    def _start_sleep_inhibition(self) -> None:
        self.sleep_inhibitor.set_enabled(self.state.prevent_sleep_during_tasks)
        if not self.state.prevent_sleep_during_tasks:
            return
        result = self.sleep_inhibitor.start()
        self._report_sleep_inhibition_start(result)

    def _report_sleep_inhibition_start(self, result: SleepInhibitionResult) -> None:
        if not result.supported:
            return
        if result.error:
            self.window.show_status(f"长任务防睡眠启用失败，任务继续执行：{result.error}")
            return
        if result.changed:
            self.window.show_status("长任务防睡眠已启用")

    def _stop_sleep_inhibition(self) -> None:
        self.sleep_inhibitor.stop()

    def _clear_zip_worker(self, thread: QThread, worker: ZipResultsWorker) -> None:
        if self._zip_thread is not thread or self._zip_worker is not worker:
            return
        self._zip_thread = None
        self._zip_worker = None

    @Slot(object)
    def _on_zip_results_ready(self, result: object) -> None:
        archive_path = getattr(result, "archive_path", None)
        packed_count = int(getattr(result, "packed_count", 0))
        skipped_count = int(getattr(result, "skipped_count", 0))
        self.state.recent_batch.packed_count = packed_count
        if isinstance(archive_path, Path):
            self.state.recent_batch.archive_path = archive_path
            self.window.set_current_output(archive_path)
            self.window.show_status(f"已打包 {packed_count} 个，跳过 {skipped_count} 个：{archive_path.name}")
            self._refresh_recent_batch_results_state()
            return
        self.window.show_status(f"已打包 {packed_count} 个，跳过 {skipped_count} 个")
        self._refresh_recent_batch_results_state()

    @Slot(str)
    def _on_zip_results_error(self, message: str) -> None:
        self.window.show_status(message)

    @Slot()
    def _on_zip_results_finished(self) -> None:
        self._zip_running = False
        self._stop_sleep_inhibition()
        self._refresh_recent_batch_results_state()

    def _last_batch_records(self) -> list[TaskRecord]:
        if not self.state.recent_batch.task_ids:
            return []
        return [
            record
            for record in self.task_model.records()
            if isinstance(record, TaskRecord) and record.task_id in self.state.recent_batch.task_ids
        ]

    def _successful_recent_batch_outputs(self) -> list[Path]:
        output_paths: list[Path] = []
        for record in self._last_batch_records():
            if record.status is not TaskStatus.succeeded or record.output_path is None:
                continue
            if record.output_path.exists():
                output_paths.append(record.output_path)
        return output_paths

    def _recent_batch_output_dir(self) -> Path | None:
        if self.state.output_dir is not None:
            return self.state.output_dir
        output_paths = self._successful_recent_batch_outputs()
        return output_paths[0].parent if output_paths else None

    def _refresh_recent_batch_results_state(self) -> None:
        records = self._last_batch_records()
        self.state.recent_batch.succeeded_count = sum(1 for record in records if record.status is TaskStatus.succeeded)
        self.state.recent_batch.failed_count = sum(1 for record in records if record.status is TaskStatus.failed)
        self.state.recent_batch.cancelled_count = sum(1 for record in records if record.status is TaskStatus.cancelled)
        has_successful_outputs = bool(self._successful_recent_batch_outputs())
        self.window.set_recent_batch_results(
            _recent_batch_summary(self.state.recent_batch, has_batch=bool(records)),
            tooltip=_recent_batch_tooltip(self.state.recent_batch, has_batch=bool(records)),
            has_batch=bool(records),
            has_successful_outputs=has_successful_outputs,
        )
        self.window.set_zip_results_enabled(
            bool(records) and has_successful_outputs and not self.state.is_batch_running,
            running=self._zip_running,
        )

    def _clear_probe_worker(self, thread: QThread, worker: ProbeWorker) -> None:
        if self._probe_thread is not thread or self._probe_worker is not worker:
            return
        self._probe_thread = None
        self._probe_worker = None
        self._probe_context = None
        self._batch_probe_error = None
        self._selection_probe_error = None
        if not self.state.is_batch_running:
            self._start_next_selection_probe()

    @Slot(object, str)
    def _on_probe_error(self, path: Path, message: str) -> None:
        if self._probe_context == "batch":
            self._batch_probe_error = message
            self.window.show_status(message)
            return
        if self._probe_context == "selection":
            self._selection_probe_error = message
            return
        if self.state.input_path != path:
            return
        self._cache_media_info(path, MediaInfo(raw={"error": message}, duration_seconds=None))
        record = self._prepared_record_for_path(path)
        if record is not None:
            record.status = TaskStatus.ready
            record.media_info = MediaInfo(raw={"error": message}, duration_seconds=None)
            record.message = "媒体信息读取失败"
            record.touch()
            self.task_model.notify_record_changed(record)
        self.window.show_status(message)

    @Slot(object, object)
    def _on_media_info(self, path: Path, media_info: MediaInfo) -> None:
        self._cache_media_info(path, media_info)
        if self._probe_context == "batch":
            self._on_batch_media_info(path, media_info)
            return
        if self._probe_context == "selection":
            self._on_selection_media_info(path, media_info)
            return
        if self.state.input_path != path:
            return
        self.state.media_info = media_info
        self.window.set_media_info(media_info)
        record = self._prepared_record_for_path(path)
        if record is not None:
            record.media_info = media_info
            record.status = TaskStatus.ready
            record.message = "媒体信息读取失败" if media_info.has_error else "已读取媒体信息"
            record.touch()
            self.task_model.notify_record_changed(record)
        if media_info.has_error:
            self.window.show_status(media_info.error_message or "ffprobe failed")
        else:
            self.window.show_status("媒体信息读取完成")
        self.window.set_start_enabled(self.state.can_start())
        self._refresh_command_preview()

    @Slot()
    def _on_probe_finished(self) -> None:
        if self._probe_context == "selection" and self._selection_probe_record is not None:
            record = self._selection_probe_record
            self._selection_probe_record = None
            message = self._selection_probe_error or "媒体信息读取失败"
            media_info = MediaInfo(raw={"error": message}, duration_seconds=None)
            self._cache_media_info(record.input_path, media_info)
            self._apply_selection_media_info(record, media_info)
            return
        if self._probe_context != "batch" or self._batch_probe_record is None:
            return
        record = self._batch_probe_record
        self._batch_probe_record = None
        message = self._batch_probe_error or "媒体信息读取失败"
        self._fail_batch_record(record, message)
        if self.state.is_batch_running:
            self._start_next_batch_task()

    def _on_batch_media_info(self, path: Path, media_info: MediaInfo) -> None:
        record = self._batch_probe_record
        if record is None or record.input_path != path:
            return
        self._batch_probe_record = None
        record.media_info = media_info
        if media_info.has_error:
            message = media_info.error_message or "媒体信息读取失败"
            self._fail_batch_record(record, message)
            self.window.show_status(f"{record.input_path.name} 跳过：{message}")
            if self.state.is_batch_running:
                self._start_next_batch_task()
            return
        record.status = TaskStatus.pending
        record.message = "已读取媒体信息"
        record.touch()
        self.task_model.notify_record_changed(record)
        self._start_batch_record(record, path)

    def _on_selection_media_info(self, path: Path, media_info: MediaInfo) -> None:
        record = self._selection_probe_record
        if record is None or record.input_path != path:
            record = self._prepared_record_for_path(path)
        if record is None:
            return
        self._selection_probe_record = None
        self._apply_selection_media_info(record, media_info)
        self._start_next_selection_probe()

    def _apply_selection_media_info(self, record: TaskRecord, media_info: MediaInfo, *, show_status: bool = True) -> None:
        record.media_info = media_info
        record.status = TaskStatus.ready
        record.progress = 0.0
        record.message = "媒体信息读取失败" if media_info.has_error else "已读取媒体信息"
        record.touch()
        self.task_model.notify_record_changed(record)
        if self.state.input_path == record.input_path:
            self.state.media_info = media_info
            self.window.set_media_info(media_info)
            self._refresh_command_preview()
        if not show_status:
            return
        if media_info.has_error:
            self.window.show_status(f"{record.input_path.name}：{media_info.error_message or '媒体信息读取失败'}")
        else:
            self.window.show_status(f"{record.input_path.name}：媒体信息读取完成")

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
                self._finish_batch(TaskStatus.cancelled)
                return
            if self._batch_queue:
                self._start_next_batch_task()
                return
            self._finish_batch()
            return

        self.window.set_busy(False)
        self._stop_sleep_inhibition()
        self.window.set_start_enabled(self.state.can_start())
        if status is TaskStatus.succeeded:
            self.window.show_status("任务完成")
        elif status is TaskStatus.cancelled:
            self.window.show_status("任务已取消")
        else:
            self.window.show_status(task.message)

    def _finish_batch(self, final_status: TaskStatus | None = None) -> None:
        final_status = final_status or self._batch_final_status()
        display_current = self.state.batch_current_index
        if final_status is not TaskStatus.cancelled:
            display_current = self._current_batch_total
        self.state.current_task = None
        self.state.is_batch_running = False
        self.state.batch_cancel_requested = False
        self.task_manager.clear_batch_cancel_flag()
        self._batch_queue.clear()
        self.window.set_busy(False)
        self._stop_sleep_inhibition()
        self.window.set_batch_buttons(pending_count=0, running=False)
        self.window.set_start_enabled(self.state.can_start())
        self.window.set_batch_progress(
            display_current,
            self._current_batch_total,
            terminal_label=_batch_finish_label(final_status),
        )
        self.window.set_progress(0.0)
        self._batch_records = []
        self._refresh_recent_batch_results_state()

    def _batch_final_status(self) -> TaskStatus:
        if any(record.status is TaskStatus.cancelled for record in self._batch_records):
            return TaskStatus.cancelled
        if any(record.status is TaskStatus.failed for record in self._batch_records):
            return TaskStatus.failed
        return TaskStatus.succeeded

    def _complete_media_info_task(self, input_path: Path) -> None:
        media_info = self.state.media_info if self.state.input_path == input_path else None
        if media_info is None:
            self._start_probe(input_path)
            self.window.show_error("媒体信息还未读取完成，请稍后再查看。")
            return
        if media_info.has_error:
            self.window.show_error(media_info.error_message or "媒体信息读取失败")
            return

        task = self._start_record_for_path(
            input_path,
            operation=Operation.media_info,
            operation_text=None,
            output_path=None,
            status=TaskStatus.succeeded,
            message="已读取媒体信息",
            progress=1.0,
        )
        self.state.current_task = task
        self.state.logs = []
        self.window.clear_log()
        self.window.set_current_output(None)
        self.window.set_progress(1.0)
        self._append_log("$ ffprobe -v error -print_format json -show_format -show_streams " + shlex.quote(str(input_path)))
        self._append_log(json.dumps(media_info.raw, ensure_ascii=False, indent=2))
        self.log_service.save_task_log(task, self.state.logs)
        self.window.show_status("媒体信息已写入日志")
        self.window.set_start_enabled(self.state.can_start())

    def _validate_duration_requirements(
        self,
        specs: list[tuple[Operation, dict[str, object], dict[str, Path]]],
        input_paths: list[Path],
    ) -> None:
        if not input_paths:
            return
        if not any(_operation_needs_media_duration(operation, options) for operation, options, _ in specs):
            return
        if len(input_paths) > 1:
            return
        if not self._duration_seconds_for_path(input_paths[0]):
            raise ValueError("淡出需要先读取媒体时长，请等待媒体信息读取完成后再开始。")

    def _options_with_media_duration(
        self,
        operation: Operation,
        options: dict[str, object],
        input_path: Path,
    ) -> dict[str, object]:
        if not _operation_needs_media_duration(operation, options):
            return options
        duration = self._duration_seconds_for_path(input_path)
        if not duration:
            raise ValueError("淡出需要先读取媒体时长，请等待媒体信息读取完成后再开始。")
        adjusted = dict(options)
        adjusted["duration_seconds"] = duration
        return adjusted

    def _mark_batch_pending(self, status: TaskStatus, message: str) -> None:
        for record, _ in self._batch_queue:
            record.status = status
            record.message = message
            record.touch()
            self.task_model.notify_record_changed(record)

    def _remove_pending_records(self, records: list[TaskRecord]) -> None:
        pending_ids = {record.task_id for record in records}
        self.task_model.remove_records(pending_ids)
        self.task_state.remove_records(pending_ids)

    def _append_log(self, line: str) -> None:
        self.state.logs.append(line)
        self.window.append_log(line)

    def _cache_media_info(self, input_path: Path, media_info: MediaInfo) -> None:
        self._media_info_cache[input_path] = media_info
        record = self._prepared_record_for_path(input_path) or self._task_record_for_path(input_path)
        if record is not None:
            record.media_info = media_info

    def _media_info_for_path(self, input_path: Path) -> MediaInfo | None:
        cached = self._media_info_cache.get(input_path)
        if cached is not None:
            return cached
        record = self._prepared_record_for_path(input_path) or self._task_record_for_path(input_path)
        if record is not None and isinstance(record.media_info, MediaInfo):
            return record.media_info
        if self.state.input_path == input_path and self.state.media_info:
            return self.state.media_info
        return None

    def _task_record_for_path(self, input_path: Path) -> TaskRecord | None:
        for record in self.task_model.records():
            if isinstance(record, TaskRecord) and record.input_path == input_path:
                return record
        return None

    def _duration_seconds_for_path(self, input_path: Path) -> float | None:
        media_info = self._media_info_for_path(input_path)
        return media_info.duration_seconds if media_info else None

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
        prevent_sleep_during_tasks = self.window.prevent_sleep_during_tasks()
        self.state.prevent_sleep_during_tasks = prevent_sleep_during_tasks
        self.sleep_inhibitor.set_enabled(prevent_sleep_during_tasks)
        config = AppConfig(
            ffmpeg_bin=self.window.selected_ffmpeg_bin(),
            ffprobe_bin=self.window.selected_ffprobe_bin(),
            output_dir=output_dir,
            prevent_sleep_during_tasks=prevent_sleep_during_tasks,
        )
        self.config_service.save(config)


def _operation_needs_media_duration(operation: Operation, options: dict[str, object]) -> bool:
    if operation is not Operation.fade:
        return False
    try:
        fade_out = float(options.get("fade_out_seconds", 0) or 0)
    except (TypeError, ValueError):
        return False
    return fade_out > 0


def _operation_needs_media_context(operation: Operation, options: dict[str, object]) -> bool:
    return operation is Operation.crop or _operation_needs_media_duration(operation, options)


def _format_command_preview(spec: CommandSpec) -> str:
    return "\n".join(_format_command_lines(spec))


def _format_command_lines(spec: CommandSpec) -> list[str]:
    command_args = [list(args) for args in spec.setup_args]
    command_args.append(spec.args)
    return ["$ " + " ".join(shlex.quote(arg) for arg in args) for args in command_args]


def _unsupported_batch_stack_operation(
    stack_specs: list[tuple[Operation, dict[str, object], dict[str, Path]]],
) -> Operation | None:
    for operation, _options, _extra_inputs in stack_specs:
        if operation not in BATCH_SUPPORTED_OPERATIONS:
            return operation
    return None


def _batch_finish_label(status: TaskStatus) -> str:
    if status is TaskStatus.cancelled:
        return "处理已取消"
    if status is TaskStatus.failed:
        return "处理结束（有失败）"
    return "处理完成"


def _recent_batch_summary(recent_batch: RecentBatchState, *, has_batch: bool) -> str:
    if not has_batch:
        return "最近批次：暂无结果"
    return (
        "最近批次："
        f"成功 {recent_batch.succeeded_count} · "
        f"失败 {recent_batch.failed_count} · "
        f"取消 {recent_batch.cancelled_count} · "
        f"已打包 {recent_batch.packed_count}"
    )


def _recent_batch_tooltip(recent_batch: RecentBatchState, *, has_batch: bool) -> str:
    if not has_batch:
        return "完成一次批处理后会显示最近批次统计"
    lines = [
        f"最近批次总数：{recent_batch.total_count}",
        f"成功：{recent_batch.succeeded_count}",
        f"失败：{recent_batch.failed_count}",
        f"取消：{recent_batch.cancelled_count}",
        f"已打包：{recent_batch.packed_count}",
    ]
    if recent_batch.archive_path is not None:
        lines.append(f"最近 ZIP：{recent_batch.archive_path}")
    return "\n".join(lines)
