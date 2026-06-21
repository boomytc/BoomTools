from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, QTimer
from PySide6.QtWidgets import QApplication

from desktop.app.services.ffmpeg_service import FfmpegService
from desktop.app.tasks.probe_worker import ProbeWorker


def test_probe_worker_cancel_stops_running_ffprobe(tmp_path: Path) -> None:
    ffprobe_script = tmp_path / "fake_ffprobe"
    ffprobe_script.write_text("#!/usr/bin/env python3\nimport time\ntime.sleep(10)\n", encoding="utf-8")
    ffprobe_script.chmod(0o755)
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"\x00")

    app = QApplication.instance() or QApplication([])
    thread = QThread()
    worker = ProbeWorker(FfmpegService(), str(ffprobe_script), input_path)
    events: list[str] = []

    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.media_info_ready.connect(lambda *_args: events.append("media"))
    worker.error_occurred.connect(lambda *_args: events.append("error"))
    worker.finished.connect(lambda: events.append("finished"))
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.start()

    QTimer.singleShot(100, lambda: worker.cancel())
    worker.finished.connect(app.quit)
    QTimer.singleShot(2000, app.quit)
    app.exec()

    if thread.isRunning():
        worker.cancel()
        thread.quit()
        thread.wait(3000)

    assert events == ["finished"]
    assert not thread.isRunning()
