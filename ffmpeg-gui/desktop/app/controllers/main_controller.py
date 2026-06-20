from __future__ import annotations

import shlex
from pathlib import Path

from PySide6.QtCore import QThread

from desktop.app.core.config import AppConfig
from desktop.app.runtime.ffmpeg import CommandError
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
from shared.contracts import MediaInfo, Operation, TaskRecord, TaskRequest, TaskResult, TaskStatus


SUBTITLE_EXTENSIONS = {".srt", ".vtt", ".ass", ".ssa"}


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
        self.window.set_start_enabled(self.state.can_start())

    def refresh_runtime_health(self) -> None:
        self._save_current_config()
        health = self.ffmpeg_service.check_health(self.window.selected_ffmpeg_bin(), self.window.selected_ffprobe_bin())
        self.state.runtime_health = health
        self.window.set_runtime_health(health)
        self.window.set_start_enabled(self.state.can_start())

    def on_input_file_selected(self, path_text: str) -> None:
        path = Path(path_text)
        self.state.input_path = path
        self.state.media_info = None
        self.window.set_media_info(None)
        self.window.reset_progress()
        self.window.set_current_output(None)
        self.window.set_start_enabled(False)
        if not path.exists():
            self.window.show_error("输入文件不存在")
            return
        self._start_probe(path)

    def on_output_dir_selected(self, path_text: str) -> None:
        path = self.output_service.normalize_output_dir(Path(path_text))
        self.state.output_dir = path
        self._save_current_config()

    def start_task(self) -> None:
        self.refresh_runtime_health()
        input_path = self.window.selected_input_path()
        output_dir = self.output_service.normalize_output_dir(self.window.selected_output_dir())
        self.state.input_path = input_path
        self.state.output_dir = output_dir

        if not input_path or not input_path.exists():
            self.window.show_error("请先选择存在的本机媒体文件")
            return
        if not self.state.runtime_health or not self.state.runtime_health.ok:
            self.window.show_error("ffmpeg 或 ffprobe 不可用，请检查路径")
            return
        if self.state.current_task and self.state.current_task.status is TaskStatus.running:
            self.window.show_error("当前已有任务在运行")
            return

        try:
            operation, options, subtitle_path = self.window.selected_operation_payload()
            self._validate_operation_inputs(operation, subtitle_path)
            request = TaskRequest(
                input_path=input_path,
                output_dir=output_dir,
                operation=operation,
                options=options,
                subtitle_path=subtitle_path,
            )
            spec = self.ffmpeg_service.build_command(self.window.selected_ffmpeg_bin(), request)
        except (CommandError, ValueError) as exc:
            self.window.show_error(str(exc))
            return

        task = TaskRecord(operation=operation, input_path=input_path, output_path=spec.output_path)
        task.progress = None if not self._duration_seconds() else 0.0
        task.message = "Running ffmpeg"
        self.state.current_task = task
        self.task_state.add(task)
        self.task_model.append_record(task)

        self.state.logs = []
        self.window.clear_log()
        self.window.set_busy(True)
        self.window.set_progress(task.progress)
        self.window.set_current_output(None)
        self._append_log("$ " + " ".join(shlex.quote(arg) for arg in spec.args))

        worker = self.task_manager.create_worker(spec, self._duration_seconds())
        worker.status_changed.connect(lambda status: self._on_task_status(task, status))
        worker.progress_changed.connect(lambda progress: self._on_task_progress(task, progress))
        worker.log_received.connect(self._append_log)
        worker.result_ready.connect(lambda result: self._on_task_result(task, result))
        worker.error_occurred.connect(lambda message: self._on_task_error(task, message))
        worker.finished.connect(lambda status: self._on_task_finished(task, worker, status))
        worker.start()

    def cancel_current_task(self) -> None:
        if self.state.current_task and self.state.current_task.status is TaskStatus.running:
            self.state.current_task.status = TaskStatus.cancelled
            self.state.current_task.message = "Cancelling"
            self.task_model.notify_record_changed(self.state.current_task)
        self.task_manager.cancel_current()

    def open_output(self) -> None:
        self.window.open_output()

    def open_output_dir(self) -> None:
        self.window.open_output_dir()

    def close(self) -> None:
        self.cancel_current_task()

    def _connect_signals(self) -> None:
        self.window.input_file_selected.connect(self.on_input_file_selected)
        self.window.output_dir_selected.connect(self.on_output_dir_selected)
        self.window.refresh_requested.connect(self.refresh_runtime_health)
        self.window.start_requested.connect(self.start_task)
        self.window.cancel_requested.connect(self.cancel_current_task)
        self.window.open_output_requested.connect(self.open_output)
        self.window.open_output_dir_requested.connect(self.open_output_dir)
        self.window.closing.connect(self.close)

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
        self.window.set_busy(False)
        self.window.set_start_enabled(self.state.can_start())
        self.task_manager.clear_current(worker)
        self.log_service.save_task_log(task, self.state.logs)
        if status is TaskStatus.succeeded:
            self.window.show_status("任务完成")
        elif status is TaskStatus.cancelled:
            self.window.show_status("任务已取消")
        else:
            self.window.show_status(task.message)

    def _append_log(self, line: str) -> None:
        self.state.logs.append(line)
        self.window.append_log(line)

    def _duration_seconds(self) -> float | None:
        return self.state.media_info.duration_seconds if self.state.media_info else None

    def _validate_operation_inputs(self, operation: Operation, subtitle_path: Path | None) -> None:
        if operation is not Operation.subtitles:
            return
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
