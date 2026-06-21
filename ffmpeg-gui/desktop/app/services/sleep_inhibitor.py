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


class CaffeinateSleepInhibitor(SleepInhibitor):
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
        command = self._command_resolver("caffeinate")
        if not command:
            return SleepInhibitionResult(
                supported=True,
                active=False,
                error="未找到 caffeinate",
            )
        try:
            self._process = self._popen_factory(
                [command, "-dimsu"],
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


def create_sleep_inhibitor(*, enabled: bool = True, platform: str = sys.platform) -> SleepInhibitor:
    if platform == "darwin":
        return CaffeinateSleepInhibitor(enabled=enabled)
    return NoopSleepInhibitor(enabled=enabled)
