from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QPushButton

from desktop.app.core.paths import QSS_PATH
from desktop.app.ui.components import PanelFrame
from desktop.app.ui.panels.command_preview_panel import CommandPreviewPanel
from desktop.app.ui.panels.runtime_panel import RuntimePanel
from desktop.app.ui.panels.stack_panel import StackPanel
from desktop.app.ui.panels.task_panel import TaskPanel
from desktop.app.ui.widgets.task_table_model import TaskTableModel


def test_runtime_panel_uses_panel_frame_and_keeps_output_action() -> None:
    _qt_app()
    panel = RuntimePanel()
    emitted: list[bool] = []
    panel.output_dir_requested.connect(lambda: emitted.append(True))

    panel.output_dir_button.click()

    assert isinstance(panel, PanelFrame)
    assert panel.title_label.text() == "内容选择"
    assert panel.body_layout().count() >= 2
    assert emitted == [True]


def test_secondary_panels_use_panel_frame_shells() -> None:
    _qt_app()
    command_panel = CommandPreviewPanel()
    stack_panel = StackPanel()
    task_panel = TaskPanel(TaskTableModel())

    assert isinstance(command_panel, PanelFrame)
    assert isinstance(stack_panel, PanelFrame)
    assert isinstance(task_panel, PanelFrame)
    assert command_panel.title_label.text() == "命令预览"
    assert stack_panel.title_label.text() == "Stack 队列"
    assert task_panel.title_label.text() == "任务队列"


def test_command_preview_keeps_input_bottom_border_visible() -> None:
    app = _qt_app()
    app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    panel = CommandPreviewPanel()
    panel.resize(1400, panel.minimumHeight())
    panel.show()
    app.processEvents()

    edit_bottom = panel.preview_edit.mapTo(panel, QPoint(0, panel.preview_edit.height())).y()

    assert panel.height() >= 96
    assert panel.height() - edit_bottom >= 8
    panel.close()


def test_stack_panel_renders_steps_as_arrow_chain() -> None:
    app = _qt_app()
    app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    panel = StackPanel()
    moved: list[tuple[int, int]] = []
    selected: list[int] = []
    panel.item_moved.connect(lambda from_index, to_index: moved.append((from_index, to_index)))
    panel.item_selected.connect(selected.append)
    panel.set_items(["旋转翻转", "缩放压缩", "画面调整"])
    panel.resize(900, panel.maximumHeight())
    panel.show()
    app.processEvents()

    chips = panel.stack_chain.findChildren(QPushButton)
    arrows = panel.stack_chain.findChildren(QLabel, "stackArrow")

    assert len(chips) == 3
    assert len(arrows) == 2
    assert [chip.text() for chip in chips] == ["1. 旋转翻转", "2. 缩放压缩", "3. 画面调整"]
    assert all(chip.property("role") == "stackChip" for chip in chips)
    assert all(chip.sizeHint().width() <= chip.width() for chip in chips)
    assert min(chip.height() for chip in chips) >= 26
    assert panel.stack_chain.height() <= 38
    assert panel.stack_chain.height() >= max(chip.height() for chip in chips) + 4
    assert "QFrame#stackChainView" not in QSS_PATH.read_text(encoding="utf-8")
    assert panel.stack_chain.selected_index() == 2
    assert panel.clear_button.parentWidget() is panel.header_widget
    assert panel.count_label.parentWidget() is panel.header_widget
    assert panel.count_label.text() == "3/6"
    assert panel.description_label.text() == "双击加入 · 拖动排序 · 最多 6 步"
    assert panel.body_layout().count() == 1
    assert panel.maximumHeight() <= 118
    assert not hasattr(panel, "move_up_button")
    assert not hasattr(panel, "move_down_button")
    assert not hasattr(panel, "add_button")
    assert not hasattr(panel, "remove_button")
    assert not hasattr(panel, "mode_label")
    assert not hasattr(panel, "list_label")

    chips[1].click()
    assert selected == [1]
    assert panel.stack_chain.selected_index() == 1

    panel.stack_chain.move_item(0, 2)

    assert moved == [(0, 2)]
    assert panel.stack_chain.selected_index() == 2
    panel.close()


def test_stack_chain_limits_six_steps_to_one_row_at_desktop_width() -> None:
    app = _qt_app()
    app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    panel = StackPanel()
    panel.set_items(
        [
            "画布补边",
            "旋转翻转",
            "裁剪",
            "画面调整",
            "音量调整",
            "去噪",
        ]
    )
    panel.resize(680, panel.maximumHeight())
    panel.show()
    app.processEvents()

    chips = panel.stack_chain.findChildren(QPushButton)
    row_tops = {chip.geometry().top() for chip in chips}

    assert len(chips) == 6
    assert len(row_tops) == 1
    assert panel.stack_chain.height() <= 38
    assert panel.count_label.text() == "6/6"
    assert all(chip.sizeHint().width() <= chip.width() for chip in chips)
    assert max(chip.geometry().right() for chip in chips) <= panel.stack_chain.width()
    assert max(chip.geometry().bottom() for chip in chips) <= panel.stack_chain.height()
    panel.close()


def test_stack_chip_drag_emits_move_request() -> None:
    app = _qt_app()
    app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    panel = StackPanel()
    moved: list[tuple[int, int]] = []
    panel.item_moved.connect(lambda from_index, to_index: moved.append((from_index, to_index)))
    panel.set_items(["旋转", "裁剪", "调色"])
    panel.resize(900, panel.maximumHeight())
    panel.show()
    app.processEvents()

    chips = panel.stack_chain.findChildren(QPushButton)
    source_chip = chips[0]
    target_position = QPoint(
        chips[2].geometry().center().x() - source_chip.geometry().left() + 10,
        source_chip.rect().center().y(),
    )

    QTest.mousePress(
        source_chip,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        source_chip.rect().center(),
    )
    QTest.mouseMove(source_chip, target_position, delay=20)
    app.processEvents()

    ghost = panel.stack_chain.findChild(QLabel, "stackDragGhost")
    marker = panel.stack_chain.findChild(QFrame, "stackDropMarker")
    assert ghost is not None
    assert marker is not None
    assert ghost.isVisible()
    assert marker.isVisible()
    assert marker.width() == 18
    assert source_chip.property("dragging") is True

    QTest.mouseRelease(source_chip, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, target_position)
    app.processEvents()

    assert moved == [(0, 2)]
    assert panel.stack_chain.selected_index() == 2
    assert not ghost.isVisible()
    assert not marker.isVisible()
    assert source_chip.property("dragging") is False
    panel.close()


def test_stack_chip_close_hit_area_emits_remove_without_selecting() -> None:
    app = _qt_app()
    app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    panel = StackPanel()
    removed: list[int] = []
    selected: list[int] = []
    panel.remove_requested.connect(removed.append)
    panel.item_selected.connect(selected.append)
    panel.set_items(["旋转", "裁剪", "调色"])
    panel.resize(900, panel.maximumHeight())
    panel.show()
    app.processEvents()

    chips = panel.stack_chain.findChildren(QPushButton)
    close_position = QPoint(chips[1].width() - 15, chips[1].height() // 2)

    QTest.mouseClick(
        chips[1],
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        close_position,
    )
    app.processEvents()

    assert removed == [1]
    assert selected == []
    assert panel.stack_chain.selected_index() == 2
    panel.close()


def test_stack_chip_close_hit_area_respects_busy_state() -> None:
    app = _qt_app()
    app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    panel = StackPanel()
    removed: list[int] = []
    panel.remove_requested.connect(removed.append)
    panel.set_items(["旋转", "裁剪"])
    panel.set_busy(True)
    panel.resize(900, panel.maximumHeight())
    panel.show()
    app.processEvents()

    chips = panel.stack_chain.findChildren(QPushButton)
    close_position = QPoint(chips[0].width() - 15, chips[0].height() // 2)

    QTest.mouseClick(
        chips[0],
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        close_position,
    )
    app.processEvents()

    assert removed == []
    assert not chips[0].isEnabled()
    panel.close()


def _qt_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        return QApplication(sys.argv)
    return app
