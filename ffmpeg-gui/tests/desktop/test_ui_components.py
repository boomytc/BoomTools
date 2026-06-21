from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton

from desktop.app.ui.components import FixedScrollArea, FormSection, PanelActionBar, PanelFrame, SegmentOption, SegmentedToggle


def test_panel_frame_exposes_title_actions_and_body_layout() -> None:
    _qt_app()
    panel = PanelFrame("任务队列", description="总进度", density="compact")
    action = QPushButton("复制")
    body_label = QLabel("内容")

    panel.add_action(action)
    panel.body_layout().addWidget(body_label)

    assert panel.objectName() == "panelFrame"
    assert panel.property("density") == "compact"
    assert panel.title_label.text() == "任务队列"
    assert panel.description_label.text() == "总进度"
    assert action.parent() is panel.header_widget
    assert panel.body_layout().count() == 1


def test_segmented_toggle_tracks_value_and_emits_changes() -> None:
    app = _qt_app()
    toggle = SegmentedToggle(
        [
            SegmentOption("single", "单操作"),
            SegmentOption("stack", "Stack 链式"),
        ]
    )
    emitted: list[str] = []
    toggle.value_changed.connect(emitted.append)

    toggle.button("stack").click()
    app.processEvents()

    assert toggle.value() == "stack"
    assert emitted == ["stack"]
    assert toggle.button("stack").property("role") == "segmentButton"


def test_segmented_toggle_skips_disabled_value() -> None:
    _qt_app()
    toggle = SegmentedToggle(
        [
            SegmentOption("single", "单操作"),
            SegmentOption("stack", "Stack 链式"),
        ]
    )

    toggle.set_option_enabled("stack", False)
    toggle.set_value("stack")

    assert toggle.value() == "single"
    assert not toggle.button("stack").isEnabled()


def test_panel_action_bar_creates_role_buttons() -> None:
    _qt_app()
    action_bar = PanelActionBar()

    primary = action_bar.add_button("开始", role="primary")
    danger = action_bar.add_button("取消", role="danger")

    assert primary.objectName() == "primaryButton"
    assert danger.property("role") == "danger"
    assert primary.property("density") == "compact"


def test_fixed_scroll_area_uses_stable_scroll_policies() -> None:
    _qt_app()
    area = FixedScrollArea(height=140, right_gutter=10)
    content = QLabel("内容")

    area.set_content_widget(content)

    assert area.widget() is content
    assert area.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert area.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded
    assert area.viewportMargins().right() == 10
    assert area.minimumHeight() == area.maximumHeight() == 140


def test_form_section_sets_form_alignment_and_empty_state() -> None:
    _qt_app()
    section = FormSection("动作参数", empty_text="当前动作无需额外参数。", field_max_width=320)
    field = QLineEdit()

    assert not section.empty_label.isHidden()

    section.add_row("输出格式", field)

    assert section.form_layout.labelAlignment() == Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
    assert field.maximumWidth() == 320
    assert section.empty_label.isHidden()


def _qt_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        return QApplication(sys.argv)
    return app
