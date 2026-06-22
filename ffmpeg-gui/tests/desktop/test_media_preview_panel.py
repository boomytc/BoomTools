from __future__ import annotations

import os
import sys
import wave
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from desktop.app.ui.panels.media_preview_panel import MediaPreviewPanel
from shared.contracts import MediaInfo, Operation, TaskRecord, TaskStatus


def test_media_preview_panel_loads_task_record_and_switches_output(tmp_path: Path) -> None:
    _qt_app()
    input_path = tmp_path / "input.mp4"
    output_path = tmp_path / "output.mp4"
    input_path.write_bytes(b"input")
    output_path.write_bytes(b"output")
    record = TaskRecord(
        operation=Operation.convert,
        input_path=input_path,
        output_path=output_path,
        media_info=MediaInfo(raw={}, duration_seconds=2.5),
        status=TaskStatus.succeeded,
    )
    panel = MediaPreviewPanel()
    _disable_player_backend(panel)

    panel.set_record(record)
    panel.source_toggle.set_value("output", emit=True)

    assert panel.current_task_id() == record.task_id
    assert panel.source_toggle.button("output").isEnabled()
    assert panel.description_label.text() == "当前任务 · 输出"
    panel.close()


def test_media_preview_panel_auto_switches_to_output_when_result_appears(tmp_path: Path) -> None:
    _qt_app()
    input_path = tmp_path / "input.wav"
    output_path = tmp_path / "output.wav"
    _write_wav(input_path)
    record = TaskRecord(
        operation=Operation.convert,
        input_path=input_path,
        output_path=output_path,
        media_info=MediaInfo(
            raw={"streams": [{"codec_type": "audio", "codec_name": "pcm_s16le"}]},
            duration_seconds=2.5,
        ),
        status=TaskStatus.running,
    )
    panel = MediaPreviewPanel()
    _disable_player_source(panel)
    panel.set_record(record)

    _write_wav(output_path)
    record.status = TaskStatus.succeeded
    panel.set_record(record)

    assert panel.source_toggle.value() == "output"
    assert panel.description_label.text() == "当前任务 · 输出"
    assert panel.player_widget.file_label.text() == "输出：output.wav"
    panel.close()


def test_media_preview_panel_preserves_manual_input_choice_after_output_exists(tmp_path: Path) -> None:
    _qt_app()
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
            duration_seconds=2.5,
        ),
        status=TaskStatus.succeeded,
    )
    panel = MediaPreviewPanel()
    _disable_player_source(panel)
    panel.set_record(record)
    panel.source_toggle.set_value("input", emit=True)

    panel.set_record(record)

    assert panel.source_toggle.value() == "input"
    assert panel.description_label.text() == "当前任务 · 输入"
    panel.close()


def test_media_preview_panel_uses_audio_placeholder_for_audio_only_input(tmp_path: Path) -> None:
    _qt_app()
    input_path = tmp_path / "voice.wav"
    _write_wav(input_path)
    record = TaskRecord(
        operation=Operation.convert,
        input_path=input_path,
        media_info=MediaInfo(
            raw={"streams": [{"codec_type": "audio", "codec_name": "mp3"}]},
            duration_seconds=3.0,
        ),
        status=TaskStatus.ready,
    )
    panel = MediaPreviewPanel()
    _disable_player_source(panel)

    panel.set_record(record)

    assert panel.player_widget.display_stack.currentWidget() is panel.player_widget.placeholder_label
    assert panel.player_widget.placeholder_label.text() == "音频预览 · 无画面"
    assert panel.player_widget.status_label.text() == "音频预览已载入"
    assert panel.player_widget.play_button.isEnabled()
    assert panel.player_widget.position_slider.isEnabled()
    panel.close()


def test_media_preview_panel_missing_output_falls_back_to_input(tmp_path: Path) -> None:
    _qt_app()
    input_path = tmp_path / "input.wav"
    missing_output_path = tmp_path / "missing-output.wav"
    _write_wav(input_path)
    record = TaskRecord(
        operation=Operation.convert,
        input_path=input_path,
        output_path=missing_output_path,
        media_info=MediaInfo(
            raw={"streams": [{"codec_type": "audio", "codec_name": "pcm_s16le"}]},
            duration_seconds=2.5,
        ),
        status=TaskStatus.succeeded,
    )
    panel = MediaPreviewPanel()
    _disable_player_source(panel)

    panel.set_record(record)

    assert panel.source_toggle.value() == "input"
    assert not panel.source_toggle.button("output").isEnabled()
    assert panel.description_label.text() == "当前任务 · 输入"
    panel.close()


def test_media_preview_panel_actions_follow_operation_and_media_state(tmp_path: Path) -> None:
    _qt_app()
    input_path = tmp_path / "input.mov"
    input_path.write_bytes(b"input")
    record = TaskRecord(operation=Operation.thumbnail, input_path=input_path, status=TaskStatus.ready)
    panel = MediaPreviewPanel()
    _disable_player_backend(panel)
    emitted_thumbnail_times: list[float] = []
    emitted_starts: list[float] = []
    panel.thumbnail_time_requested.connect(emitted_thumbnail_times.append)
    panel.trim_start_requested.connect(emitted_starts.append)

    panel.set_record(record)
    panel.set_operation(Operation.convert)
    assert not panel.thumbnail_time_button.isEnabled()
    assert panel.set_start_button.isEnabled()

    panel.set_operation(Operation.thumbnail)
    assert panel.thumbnail_time_button.isEnabled()
    panel.thumbnail_time_button.click()
    panel.set_start_button.click()

    assert emitted_thumbnail_times == [0.0]
    assert emitted_starts == [0.0]
    panel.close()


def test_media_preview_panel_tracks_trim_summary(tmp_path: Path) -> None:
    _qt_app()
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"input")
    record = TaskRecord(operation=Operation.convert, input_path=input_path, status=TaskStatus.ready)
    panel = MediaPreviewPanel()
    _disable_player_backend(panel)
    panel.set_record(record)

    panel.set_trim_range(1.2, None)

    assert panel.range_summary_label.text() == "范围：1.2 - --"
    assert panel.clear_range_button.isEnabled()
    panel.close()


def test_media_preview_source_toggle_stays_below_header() -> None:
    app = _qt_app()
    panel = MediaPreviewPanel()
    panel.resize(320, 620)
    panel.show()
    app.processEvents()

    toggle_top = panel.source_toggle.mapTo(panel, QPoint(0, 0)).y()
    header_bottom = panel.header_widget.mapTo(panel, QPoint(0, panel.header_widget.height())).y()

    assert panel.source_toggle.parentWidget().objectName() == "mediaPreviewSourceBar"
    assert panel.source_toggle.parentWidget().parentWidget() is panel.body_widget
    assert toggle_top >= header_bottom
    panel.close()


def test_media_preview_control_icons_use_light_foreground() -> None:
    _qt_app()
    panel = MediaPreviewPanel()

    for button in (
        panel.player_widget.play_button,
        panel.player_widget.pause_button,
        panel.player_widget.stop_button,
    ):
        colors = _opaque_icon_colors(button.icon(), button.iconSize())

        assert colors
        assert min(color.red() for color in colors) >= 230
        assert min(color.green() for color in colors) >= 230
        assert min(color.blue() for color in colors) >= 230

    panel.close()


def _qt_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        return QApplication(sys.argv)
    return app


def _disable_player_backend(panel: MediaPreviewPanel) -> None:
    panel.player_widget.set_media = lambda *_args, **_kwargs: None  # type: ignore[method-assign]
    panel.player_widget.clear = lambda *_args, **_kwargs: None  # type: ignore[method-assign]


def _disable_player_source(panel: MediaPreviewPanel) -> None:
    player = panel.player_widget
    player._player.setSource = lambda *_args, **_kwargs: None  # type: ignore[method-assign]


def _write_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"\x00\x00" * 32)


def _opaque_icon_colors(icon: QIcon, size) -> list:
    image = icon.pixmap(size, QIcon.Mode.Normal, QIcon.State.Off).toImage()
    return [
        image.pixelColor(x, y)
        for y in range(image.height())
        for x in range(image.width())
        if image.pixelColor(x, y).alpha() > 0
    ]
