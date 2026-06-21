from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, QTimer
from PySide6.QtWidgets import QApplication

from desktop.app.tasks.health_worker import HealthWorker


def test_health_worker_cancel_stops_running_version_probe(tmp_path: Path) -> None:
    ffmpeg_script = tmp_path / "fake_ffmpeg"
    ffprobe_script = tmp_path / "fake_ffprobe"
    ffmpeg_script.write_text("#!/usr/bin/env python3\nimport time\ntime.sleep(10)\n", encoding="utf-8")
    ffprobe_script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    ffmpeg_script.chmod(0o755)
    ffprobe_script.chmod(0o755)

    app = QApplication.instance() or QApplication([])
    thread = QThread()
    worker = HealthWorker(str(ffmpeg_script), str(ffprobe_script))
    events: list[str] = []

    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.health_ready.connect(lambda *_args: events.append("health"))
    worker.finished.connect(lambda: events.append("finished"))
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.start()

    QTimer.singleShot(100, worker.cancel)
    worker.finished.connect(app.quit)
    QTimer.singleShot(2000, app.quit)
    app.exec()

    if thread.isRunning():
        worker.cancel()
        thread.quit()
        thread.wait(3000)

    assert events == ["finished"]
    assert not thread.isRunning()
