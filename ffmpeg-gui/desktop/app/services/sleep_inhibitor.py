from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable, Protocol


class _Process(Protocol):
    def poll(self) -> int | None: ...

    def terminate(self) -> None: ...

    def kill(self) -> None: ...

    def wait(self, timeout: float | None = None) -> int: ...


@dataclass(frozen=True)
class SleepInhibitionResult:
    supported: bool
    active: bool
    changed: bool = False
    error: str | None = None


class SleepInhibitor:
    @property
    def active(self) -> bool:
        return False

    def set_enabled(self, enabled: bool) -> None:
        return None

    def start(self) -> SleepInhibitionResult:
        return SleepInhibitionResult(supported=False, active=False)

    def stop(self) -> None:
        return None


class NoopSleepInhibitor(SleepInhibitor):
    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled


class _SleepInhibitorSetupError(RuntimeError):
    pass


class _SubprocessSleepInhibitor(SleepInhibitor):
    command_name = ""
    missing_message = ""

    def __init__(
        self,
        *,
        enabled: bool = True,
        command_resolver: Callable[[str], str | None] = shutil.which,
        popen_factory: Callable[..., _Process] = subprocess.Popen,
        stop_timeout_seconds: float = 2.0,
    ) -> None:
        self.enabled = enabled
        self._command_resolver = command_resolver
        self._popen_factory = popen_factory
        self._stop_timeout_seconds = stop_timeout_seconds
        self._process: _Process | None = None

    @property
    def active(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        if not enabled:
            self.stop()

    def start(self) -> SleepInhibitionResult:
        if not self.enabled:
            return SleepInhibitionResult(supported=True, active=False)
        if self.active:
            return SleepInhibitionResult(supported=True, active=True)
        self._process = None
        command = self._command_resolver(self.command_name)
        if not command:
            return SleepInhibitionResult(
                supported=True,
                active=False,
                error=self.missing_message,
            )
        try:
            args = self._command_args(command)
        except _SleepInhibitorSetupError as exc:
            return SleepInhibitionResult(
                supported=True,
                active=False,
                error=str(exc),
            )
        try:
            self._process = self._popen_factory(
                args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            self._process = None
            return SleepInhibitionResult(
                supported=True,
                active=False,
                error=str(exc),
            )
        returncode = self._process.poll()
        if returncode is not None:
            self._process = None
            return SleepInhibitionResult(
                supported=True,
                active=False,
                error=f"{self.command_name} 已退出，返回码 {returncode}",
            )
        return SleepInhibitionResult(supported=True, active=True, changed=True)

    def stop(self) -> None:
        process = self._process
        self._process = None
        if process is None or process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=self._stop_timeout_seconds)
        except (OSError, subprocess.TimeoutExpired):
            try:
                process.kill()
                process.wait(timeout=self._stop_timeout_seconds)
            except (OSError, subprocess.TimeoutExpired):
                return

    def _command_args(self, command: str) -> list[str]:
        raise NotImplementedError


class CaffeinateSleepInhibitor(_SubprocessSleepInhibitor):
    command_name = "caffeinate"
    missing_message = "未找到 caffeinate"

    def _command_args(self, command: str) -> list[str]:
        return [command, "-dimsu"]


class SystemdInhibitSleepInhibitor(_SubprocessSleepInhibitor):
    command_name = "systemd-inhibit"
    missing_message = "未找到 systemd-inhibit"

    def _command_args(self, command: str) -> list[str]:
        sleep_command = self._command_resolver("sleep")
        if not sleep_command:
            raise _SleepInhibitorSetupError("未找到 sleep")
        return [
            command,
            "--what=sleep:idle",
            "--who=ffmpeg-gui",
            "--why=ffmpeg-gui long-running task",
            "--mode=block",
            sleep_command,
            "infinity",
        ]


class WindowsSleepInhibitor(SleepInhibitor):
    ES_SYSTEM_REQUIRED = 0x00000001
    ES_DISPLAY_REQUIRED = 0x00000002
    ES_CONTINUOUS = 0x80000000
    INHIBIT_FLAGS = ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED

    def __init__(
        self,
        *,
        enabled: bool = True,
        execution_state_setter: Callable[[int], int] | None = None,
    ) -> None:
        self.enabled = enabled
        self._execution_state_setter = execution_state_setter
        self._active = False

    @property
    def active(self) -> bool:
        return self._active

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        if not enabled:
            self.stop()

    def start(self) -> SleepInhibitionResult:
        if not self.enabled:
            return SleepInhibitionResult(supported=True, active=False)
        if self.active:
            return SleepInhibitionResult(supported=True, active=True)
        try:
            result = self._set_execution_state(self.INHIBIT_FLAGS)
        except Exception as exc:
            return SleepInhibitionResult(supported=True, active=False, error=str(exc))
        if result == 0:
            return SleepInhibitionResult(
                supported=True,
                active=False,
                error="SetThreadExecutionState 调用失败",
            )
        self._active = True
        return SleepInhibitionResult(supported=True, active=True, changed=True)

    def stop(self) -> None:
        if not self.active:
            return
        try:
            self._set_execution_state(self.ES_CONTINUOUS)
        except Exception:
            pass
        self._active = False

    def _set_execution_state(self, flags: int) -> int:
        setter = self._execution_state_setter
        if setter is None:
            import ctypes

            try:
                setter = ctypes.windll.kernel32.SetThreadExecutionState  # type: ignore[attr-defined]
            except AttributeError as exc:
                raise RuntimeError("当前平台不支持 Windows 防睡眠 API") from exc
            self._execution_state_setter = setter
        return int(setter(flags))


def create_sleep_inhibitor(*, enabled: bool = True, platform: str = sys.platform) -> SleepInhibitor:
    normalized_platform = platform.lower()
    if normalized_platform == "darwin":
        return CaffeinateSleepInhibitor(enabled=enabled)
    if normalized_platform.startswith("win"):
        return WindowsSleepInhibitor(enabled=enabled)
    if normalized_platform.startswith("linux"):
        return SystemdInhibitSleepInhibitor(enabled=enabled)
    return NoopSleepInhibitor(enabled=enabled)
