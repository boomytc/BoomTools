from __future__ import annotations

import subprocess

from desktop.app.services.sleep_inhibitor import CaffeinateSleepInhibitor, NoopSleepInhibitor, create_sleep_inhibitor


class _FakeProcess:
    def __init__(self, *, timeout_on_first_wait: bool = False, timeout_after_kill: bool = False) -> None:
        self.poll_value: int | None = None
        self.terminate_count = 0
        self.kill_count = 0
        self.wait_count = 0
        self.timeout_on_first_wait = timeout_on_first_wait
        self.timeout_after_kill = timeout_after_kill

    def poll(self) -> int | None:
        return self.poll_value

    def terminate(self) -> None:
        self.terminate_count += 1
        if not self.timeout_on_first_wait:
            self.poll_value = 0

    def kill(self) -> None:
        self.kill_count += 1
        self.poll_value = -9

    def wait(self, timeout: float | None = None) -> int:
        self.wait_count += 1
        if self.timeout_on_first_wait and self.kill_count == 0:
            raise subprocess.TimeoutExpired("caffeinate", timeout)
        if self.timeout_after_kill and self.kill_count > 0:
            raise subprocess.TimeoutExpired("caffeinate", timeout)
        return self.poll_value or 0


def test_caffeinate_inhibitor_start_stop_are_idempotent() -> None:
    created_args: list[list[str]] = []
    processes: list[_FakeProcess] = []

    def popen_factory(args: list[str], **_: object) -> _FakeProcess:
        process = _FakeProcess()
        created_args.append(args)
        processes.append(process)
        return process

    inhibitor = CaffeinateSleepInhibitor(
        command_resolver=lambda _: "/usr/bin/caffeinate",
        popen_factory=popen_factory,
    )

    first = inhibitor.start()
    second = inhibitor.start()
    inhibitor.stop()
    inhibitor.stop()

    assert first.supported
    assert first.active
    assert first.changed
    assert second.supported
    assert second.active
    assert not second.changed
    assert created_args == [["/usr/bin/caffeinate", "-dimsu"]]
    assert processes[0].terminate_count == 1
    assert processes[0].kill_count == 0


def test_caffeinate_inhibitor_reports_missing_command_without_blocking() -> None:
    inhibitor = CaffeinateSleepInhibitor(command_resolver=lambda _: None)

    result = inhibitor.start()

    assert result.supported
    assert not result.active
    assert result.error == "未找到 caffeinate"


def test_caffeinate_inhibitor_kills_process_after_stop_timeout() -> None:
    processes: list[_FakeProcess] = []

    def popen_factory(args: list[str], **_: object) -> _FakeProcess:
        process = _FakeProcess(timeout_on_first_wait=True)
        processes.append(process)
        return process

    inhibitor = CaffeinateSleepInhibitor(
        command_resolver=lambda _: "/usr/bin/caffeinate",
        popen_factory=popen_factory,
        stop_timeout_seconds=0.01,
    )

    inhibitor.start()
    inhibitor.stop()

    assert processes[0].terminate_count == 1
    assert processes[0].kill_count == 1
    assert processes[0].wait_count == 2


def test_caffeinate_inhibitor_suppresses_timeout_after_kill() -> None:
    processes: list[_FakeProcess] = []

    def popen_factory(args: list[str], **_: object) -> _FakeProcess:
        process = _FakeProcess(timeout_on_first_wait=True, timeout_after_kill=True)
        processes.append(process)
        return process

    inhibitor = CaffeinateSleepInhibitor(
        command_resolver=lambda _: "/usr/bin/caffeinate",
        popen_factory=popen_factory,
        stop_timeout_seconds=0.01,
    )

    inhibitor.start()
    inhibitor.stop()

    assert processes[0].terminate_count == 1
    assert processes[0].kill_count == 1
    assert processes[0].wait_count == 2


def test_disabling_caffeinate_inhibitor_stops_running_process() -> None:
    processes: list[_FakeProcess] = []

    def popen_factory(args: list[str], **_: object) -> _FakeProcess:
        process = _FakeProcess()
        processes.append(process)
        return process

    inhibitor = CaffeinateSleepInhibitor(
        command_resolver=lambda _: "/usr/bin/caffeinate",
        popen_factory=popen_factory,
    )

    inhibitor.start()
    inhibitor.set_enabled(False)

    assert processes[0].terminate_count == 1
    assert not inhibitor.active


def test_create_sleep_inhibitor_uses_noop_off_macos() -> None:
    inhibitor = create_sleep_inhibitor(platform="linux")

    result = inhibitor.start()
    inhibitor.stop()
    inhibitor.set_enabled(False)

    assert isinstance(inhibitor, NoopSleepInhibitor)
    assert not result.supported
    assert not result.active
