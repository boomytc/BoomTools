from __future__ import annotations

import logging

from .paths import LOGS_DIR, ensure_runtime_dirs


def configure_logging() -> None:
    ensure_runtime_dirs()
    log_path = LOGS_DIR / "ffmpeg-gui.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
