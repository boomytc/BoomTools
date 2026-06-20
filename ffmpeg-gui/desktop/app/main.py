from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from desktop.app.bootstrap import create_app
from desktop.app.core.constants import APP_NAME
from desktop.app.core.logging import configure_logging
from desktop.app.core.paths import QSS_PATH, ensure_runtime_dirs


def main() -> int:
    ensure_runtime_dirs()
    configure_logging()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    _load_qss(app)
    bootstrap = create_app()
    app.aboutToQuit.connect(bootstrap.controller.close)
    bootstrap.window.show()
    return app.exec()


def _load_qss(app: QApplication) -> None:
    if not QSS_PATH.exists():
        return
    try:
        app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    except OSError:
        logging.exception("Failed to load QSS")


if __name__ == "__main__":
    raise SystemExit(main())
