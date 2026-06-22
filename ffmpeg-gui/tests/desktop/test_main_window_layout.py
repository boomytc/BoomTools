from __future__ import annotations

import os
import sys
import wave
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QFrame, QWidget

from desktop.app.core.paths import QSS_PATH
from desktop.app.ui.main_window import MainWindow
from desktop.app.ui.widgets.task_table_model import TaskTableModel
from shared.contracts import MediaInfo, Operation, TaskRecord, TaskStatus


def test_main_window_builds_dashboard_layout_host() -> None:
    app = _qt_app()
    app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    window = MainWindow(TaskTableModel())
    window.show()
    app.processEvents()

    dashboard = window.findChild(QWidget, "dashboardLayoutHost")

    assert dashboard is window.dashboard_layout
    assert window.runtime_panel.property("panel_id") == "content"
    assert window.operation_panel.operation_form.operation_selector.property("panel_id") == "operation"
    assert window.operation_panel.operation_form.parameter_form.property("panel_id") == "parameters"
    assert window.operation_panel.stack_panel.property("panel_id") == "stack"
    assert window.command_preview_panel.property("panel_id") == "command_preview"
    assert window.media_preview_panel.property("panel_id") == "media_preview"
    assert window.task_panel.property("panel_id") == "tasks"
    assert window.dashboard_layout.workflow_splitter.widget(0) is window.operation_panel
    assert window.dashboard_layout.workflow_splitter.widget(1) is window.task_panel
    assert window.dashboard_layout.content_splitter.widget(1) is window.media_preview_panel

    window.close()


def test_main_window_default_panel_order_and_resize_bounds() -> None:
    app = _qt_app()
    app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    window = MainWindow(TaskTableModel())
    window.resize(1320, 1000)
    window.show()
    app.processEvents()

    masthead = window.findChild(QFrame, "masthead")
    assert masthead is not None
    runtime_top = _top_in_window(window.runtime_panel, window)
    operation_top = _top_in_window(window.operation_panel, window)
    command_top = _top_in_window(window.command_preview_panel, window)
    task_top = _top_in_window(window.task_panel, window)
    operation_selector = window.operation_panel.operation_form.operation_selector
    parameter_form = window.operation_panel.operation_form.parameter_form
    preview_top = _top_in_window(window.media_preview_panel, window)
    operation_selector_top = _top_in_window(operation_selector, window)
    parameter_form_top = _top_in_window(parameter_form, window)
    command_bottom = _bottom_in_window(window.command_preview_panel, window)
    parameter_bottom = _bottom_in_window(parameter_form, window)

    assert runtime_top > _top_in_window(masthead, window)
    assert runtime_top < operation_top < command_top < task_top
    assert runtime_top < preview_top
    assert command_top < _bottom_in_window(window.operation_panel, window)
    assert abs(operation_selector_top - parameter_form_top) <= 2
    assert abs(parameter_bottom - command_bottom) <= 2
    assert abs(window.command_preview_panel.width() - operation_selector.width()) <= 2
    assert window.task_panel.height() > window.task_panel.minimumHeight()
    assert window.task_panel.task_table.height() >= 180
    assert window.operation_panel.height() <= window.operation_panel.sizeHint().height() + 2

    window.resize(1320, 760)
    app.processEvents()

    assert window.runtime_panel.height() <= window.runtime_panel.maximumHeight()
    assert window.operation_panel.height() <= window.operation_panel.sizeHint().height() + 2
    assert window.task_panel.height() >= window.task_panel.minimumHeight()
    assert window.dashboard_layout.workflow_splitter.sizes()[1] >= window.task_panel.minimumHeight()
    window.close()


def test_main_window_preview_layout_holds_across_common_widths(tmp_path: Path) -> None:
    app = _qt_app()
    app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    input_path = tmp_path / "input.wav"
    output_path = tmp_path / "output.wav"
    _write_wav(input_path)
    _write_wav(output_path)
    record = TaskRecord(
        operation=Operation.convert,
        input_path=input_path,
        output_path=output_path,
        media_info=MediaInfo(
            raw={"streams": [{"codec_type": "audio", "codec_name": "pcm_s16le"}]},
            duration_seconds=53.0,
        ),
        status=TaskStatus.succeeded,
    )
    task_model = TaskTableModel()
    task_model.set_records([record])
    window = MainWindow(task_model)
    player = window.media_preview_panel.player_widget
    player._player.setSource = lambda *_args, **_kwargs: None  # type: ignore[method-assign]
    window.set_preview_record(record)
    window.show()

    for width in (1600, 1440, 1320, 1180, 1080):
        window.resize(width, 920)
        app.processEvents()

        central = window.centralWidget()
        selector = window.operation_panel.operation_form.operation_selector
        operation_content = selector.operation_grid_widget
        operation_viewport = selector.operation_scroll_area.viewport()
        preview_panel = window.media_preview_panel
        player = preview_panel.player_widget

        assert _left_in(preview_panel, central) >= 0
        assert _right_in(preview_panel, central) <= central.width()
        assert preview_panel.maximumWidth() > 1000
        assert _right_in(preview_panel.source_toggle, preview_panel) <= preview_panel.width()
        assert _right_in(player.time_label, player) <= player.width()
        assert _right_in(player.position_slider, player) <= _left_in(player.time_label, player)
        assert operation_content.width() <= operation_viewport.width() + 2
        assert selector.operation_scroll_area.horizontalScrollBar().maximum() == 0
        assert window.operation_panel.operation_form.operation_selector.geometry().right() < (
            window.operation_panel.operation_form.parameter_form.geometry().left()
        )

    window.close()


def _top_in_window(widget: QWidget, window: MainWindow) -> int:
    return widget.mapTo(window, QPoint(0, 0)).y()


def _bottom_in_window(widget: QWidget, window: MainWindow) -> int:
    return widget.mapTo(window, QPoint(0, widget.height())).y()


def _left_in(widget: QWidget, container: QWidget) -> int:
    return widget.mapTo(container, QPoint(0, 0)).x()


def _right_in(widget: QWidget, container: QWidget) -> int:
    return widget.mapTo(container, QPoint(widget.width(), 0)).x()


def _write_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"\x00\x00" * 32)


def _qt_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        return QApplication(sys.argv)
    return app
