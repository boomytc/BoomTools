from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from desktop.app.ui.dialogs.settings_dialog import SettingsDialog


def test_settings_dialog_exposes_prevent_sleep_toggle() -> None:
    app = _qt_app()
    dialog = SettingsDialog()

    dialog.set_initial_paths(
        ffmpeg_bin="ffmpeg",
        ffprobe_bin="ffprobe",
        prevent_sleep_during_tasks=False,
    )
    app.processEvents()

    assert dialog.prevent_sleep_during_tasks() is False

    dialog.prevent_sleep_checkbox.setChecked(True)
    assert dialog.prevent_sleep_during_tasks() is True

    dialog.close()


def test_settings_dialog_disables_prevent_sleep_toggle_while_busy() -> None:
    _qt_app()
    dialog = SettingsDialog()

    dialog.set_busy(True)
    assert not dialog.prevent_sleep_checkbox.isEnabled()

    dialog.set_busy(False)
    assert dialog.prevent_sleep_checkbox.isEnabled()

    dialog.close()


def _qt_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        return QApplication(sys.argv)
    return app
