from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, Signal

from desktop.app.runtime.ffmpeg import CommandSpec, parse_progress_line
from shared.contracts import TaskResult, TaskStatus


class FfmpegProcessWorker(QObject):
    status_changed = Signal(object)
    progress_changed = Signal(object)
    log_received = Signal(str)
    result_ready = Signal(object)
    error_occurred = Signal(str)
    finished = Signal(object)

    def __init__(self, spec: CommandSpec, duration_seconds: float | None) -> None:
        super().__init__()
        self._spec = spec
        self._duration_seconds = duration_seconds
        self._process: QProcess | None = None
        self._stdout_buffer = ""
        self._stderr_buffer = ""
        self._cancel_requested = False
        self._stage_args: list[list[str]] = []
        self._stage_index = 0
        self._cleanup_done = False

    def start(self) -> None:
        self._cancel_requested = False
        self.status_changed.emit(TaskStatus.running)
        self._stage_args = [list(stage) for stage in self._spec.setup_args] + [self._spec.args]
        self._stage_index = 0
        self._start_current_stage()

    def _start_current_stage(self) -> None:
        self._process = QProcess(self)
        self._process.setProcessEnvironment(QProcessEnvironment.systemEnvironment())
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self._process.readyReadStandardOutput.connect(self._read_stdout)
        self._process.readyReadStandardError.connect(self._read_stderr)
        self._process.errorOccurred.connect(self._handle_error)
        self._process.finished.connect(self._handle_finished)
        args = self._stage_args[self._stage_index]
        self._process.start(args[0], args[1:])

    def cancel(self) -> None:
        self._cancel_requested = True
        if not self._process:
            self._cleanup_temp_paths()
            self.status_changed.emit(TaskStatus.cancelled)
            self.finished.emit(TaskStatus.cancelled)
            return
        if self._process.state() == QProcess.ProcessState.NotRunning:
            self._cleanup_temp_paths()
            return
        self.log_received.emit("Cancelling ffmpeg process...")
        self._process.terminate()
        QTimer.singleShot(3000, self._kill_if_still_running)

    def cancel_and_wait(self, wait_msecs: int = 1500) -> None:
        self._cancel_requested = True
        if not self._process:
            self._cleanup_temp_paths()
            return
        if self._process.state() == QProcess.ProcessState.NotRunning:
            self._cleanup_temp_paths()
            return
        self.log_received.emit("Cancelling ffmpeg process...")
        self._process.terminate()
        if self._process.waitForFinished(wait_msecs):
            self._cleanup_temp_paths()
            return
        self.log_received.emit("ffmpeg did not exit after terminate; killing process.")
        self._process.kill()
        self._process.waitForFinished(wait_msecs)
        self._cleanup_temp_paths()

    def _read_stdout(self) -> None:
        if not self._process:
            return
        chunk = bytes(self._process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self._stdout_buffer += chunk
        while "\n" in self._stdout_buffer:
            line, self._stdout_buffer = self._stdout_buffer.split("\n", 1)
            self._handle_progress_line(line.strip())

    def _read_stderr(self) -> None:
        if not self._process:
            return
        chunk = bytes(self._process.readAllStandardError()).decode("utf-8", errors="replace")
        self._stderr_buffer += chunk
        while "\n" in self._stderr_buffer:
            line, self._stderr_buffer = self._stderr_buffer.split("\n", 1)
            line = line.rstrip()
            if line:
                self.log_received.emit(line)

    def _handle_progress_line(self, line: str) -> None:
        if not line:
            return
        if line == "progress=end":
            self.progress_changed.emit(1.0)
            return
        progress = parse_progress_line(line, self._duration_seconds)
        if progress is not None:
            self.progress_changed.emit(progress)

    def _handle_error(self, error: QProcess.ProcessError) -> None:
        if self._cancel_requested:
            return
        self.error_occurred.emit(f"QProcess error: {error.name}")
        if error == QProcess.ProcessError.FailedToStart:
            self._cleanup_temp_paths()
            self.status_changed.emit(TaskStatus.failed)
            self.finished.emit(TaskStatus.failed)

    def _handle_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        if self._stderr_buffer.strip():
            self.log_received.emit(self._stderr_buffer.strip())
            self._stderr_buffer = ""
        if self._stdout_buffer.strip():
            self._handle_progress_line(self._stdout_buffer.strip())
            self._stdout_buffer = ""

        if self._cancel_requested:
            self._cleanup_temp_paths()
            self.status_changed.emit(TaskStatus.cancelled)
            self.finished.emit(TaskStatus.cancelled)
            return

        if exit_status == QProcess.ExitStatus.NormalExit and exit_code == 0:
            if self._stage_index < len(self._stage_args) - 1:
                self._stage_index += 1
                self._start_current_stage()
                return
            if self._spec.output_path is None:
                self.progress_changed.emit(1.0)
                self.status_changed.emit(TaskStatus.succeeded)
                self.result_ready.emit(TaskResult(output_path=None, output_size=0))
                self._cleanup_temp_paths()
                self.finished.emit(TaskStatus.succeeded)
                return
            if self._spec.output_path.exists():
                self.progress_changed.emit(1.0)
                self.status_changed.emit(TaskStatus.succeeded)
                self.result_ready.emit(
                    TaskResult(output_path=self._spec.output_path, output_size=self._spec.output_path.stat().st_size)
                )
                self._cleanup_temp_paths()
                self.finished.emit(TaskStatus.succeeded)
                return

        message = f"ffmpeg exited with code {exit_code}"
        if exit_code == 0:
            if self._spec.output_path is None:
                message = "ffmpeg exited without output file"
            elif not self._spec.output_path.exists():
                message = f"ffmpeg output missing: {self._spec.output_path}"
        self.error_occurred.emit(message)
        self.status_changed.emit(TaskStatus.failed)
        self._cleanup_temp_paths()
        self.finished.emit(TaskStatus.failed)
        return

    def _kill_if_still_running(self) -> None:
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            self.log_received.emit("ffmpeg did not exit after terminate; killing process.")
            self._process.kill()

    @property
    def output_path(self) -> Path | None:
        return self._spec.output_path

    def _cleanup_temp_paths(self) -> None:
        if self._cleanup_done:
            return
        self._cleanup_done = True
        for path in self._spec.cleanup_paths:
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                self.log_received.emit(f"Failed to remove temporary file {path}: {exc}")
