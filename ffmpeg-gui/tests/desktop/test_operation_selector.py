from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from desktop.app.ui.widgets.operation_selector import OperationSelector
from shared.contracts import Operation


def test_operation_selector_selects_operation_and_emits_change() -> None:
    _qt_app()
    selector = OperationSelector()
    emitted: list[Operation] = []
    selector.operation_changed.connect(emitted.append)

    selector.select_operation(Operation.raw)

    assert selector.selected_operation() is Operation.raw
    assert emitted == [Operation.raw]
    assert selector.operation_buttons()[Operation.raw].isChecked()


def test_operation_selector_disables_unsupported_batch_operations() -> None:
    _qt_app()
    selector = OperationSelector()

    selector.set_batch_operation_support(True, {Operation.convert, Operation.compress})

    assert selector.operation_buttons()[Operation.convert].isEnabled()
    assert not selector.operation_buttons()[Operation.thumbnail].isEnabled()
    assert "多个文件暂不支持" in selector.operation_buttons()[Operation.thumbnail].toolTip()


def test_operation_selector_disables_unsupported_stack_operations() -> None:
    _qt_app()
    selector = OperationSelector()
    emitted: list[Operation] = []
    selector.operation_changed.connect(emitted.append)

    selector.set_stack_mode(True)

    assert selector.stack_mode()
    assert selector.selected_operation() is Operation.rotate
    assert emitted == [Operation.rotate]
    assert selector.operation_buttons()[Operation.rotate].isEnabled()
    assert selector.operation_buttons()[Operation.crop].isEnabled()
    assert not selector.operation_buttons()[Operation.convert].isEnabled()
    assert not selector.operation_buttons()[Operation.raw].isEnabled()
    assert "Stack 仅支持可链式单输入滤镜" in selector.operation_buttons()[Operation.convert].toolTip()


def test_operation_selector_restores_single_operation_choices_after_stack_mode() -> None:
    _qt_app()
    selector = OperationSelector()

    selector.set_stack_mode(True)
    selector.select_operation(Operation.raw)
    assert selector.selected_operation() is Operation.rotate

    selector.set_stack_mode(False)
    selector.select_operation(Operation.raw)

    assert selector.operation_buttons()[Operation.raw].isEnabled()
    assert selector.selected_operation() is Operation.raw


def test_operation_selector_segmented_toggle_emits_stack_mode() -> None:
    _qt_app()
    selector = OperationSelector()
    emitted: list[bool] = []
    selector.stack_mode_toggled.connect(emitted.append)

    selector.mode_toggle.button("stack").click()

    assert selector.stack_mode()
    assert emitted == [True]


def _qt_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        return QApplication(sys.argv)
    return app
