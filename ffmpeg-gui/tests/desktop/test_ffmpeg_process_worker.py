from __future__ import annotations

import os
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from desktop.app.runtime.ffmpeg import CommandSpec
from desktop.app.tasks.ffmpeg_process import FfmpegProcessWorker
from shared.contracts import TaskResult, TaskStatus


def test_ffmpeg_process_worker_runs_setup_stage_and_cleans_temp_file(tmp_path: Path) -> None:
    script = tmp_path / "fake_stage.py"
    script.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "import sys",
                "mode = sys.argv[1]",
                "path = Path(sys.argv[2])",
                "path.write_text(mode, encoding='utf-8')",
                "if mode == 'final':",
                "    print('progress=end', flush=True)",
            ]
        ),
        encoding="utf-8",
    )
    palette_path = tmp_path / "palette.png"
    output_path = tmp_path / "output.gif"
    spec = CommandSpec(
        args=[sys.executable, str(script), "final", str(output_path)],
        output_path=output_path,
        output_name=output_path.name,
        setup_args=((sys.executable, str(script), "palette", str(palette_path)),),
        cleanup_paths=(palette_path,),
    )
    app = QApplication.instance() or QApplication([])
    worker = FfmpegProcessWorker(spec, duration_seconds=None)
    statuses: list[TaskStatus] = []
    results: list[TaskResult] = []
    finished: list[TaskStatus] = []

    worker.status_changed.connect(statuses.append)
    worker.result_ready.connect(results.append)
    worker.finished.connect(finished.append)
    worker.start()

    deadline = time.monotonic() + 3
    while not finished and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)

    assert finished == [TaskStatus.succeeded]
    assert statuses[-1] is TaskStatus.succeeded
    assert results[0].output_path == output_path
    assert output_path.read_text(encoding="utf-8") == "final"
    assert not palette_path.exists()
