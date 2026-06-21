from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QSizePolicy, QWidget


@dataclass(frozen=True)
class SegmentOption:
    value: str
    label: str
    tooltip: str = ""
    enabled: bool = True


class SegmentedToggle(QWidget):
    value_changed = Signal(str)

    def __init__(self, options: list[SegmentOption] | None = None) -> None:
        super().__init__()
        self.setObjectName("segmentedToggle")
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self._buttons: dict[str, QPushButton] = {}
        self._value = ""

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        if options:
            self.set_options(options)

    def set_options(self, options: list[SegmentOption]) -> None:
        self._clear()
        for option in options:
            button = QPushButton(option.label)
            button.setCheckable(True)
            button.setEnabled(option.enabled)
            button.setProperty("role", "segmentButton")
            if option.tooltip:
                button.setToolTip(option.tooltip)
            button.clicked.connect(lambda _checked=False, value=option.value: self.set_value(value, emit=True))
            self._buttons[option.value] = button
            self._group.addButton(button)
            self._layout.addWidget(button)
        if options:
            self.set_value(options[0].value, emit=False)

    def value(self) -> str:
        return self._value

    def set_value(self, value: str, *, emit: bool = False, force: bool = False) -> None:
        if value not in self._buttons:
            raise ValueError(f"Unknown segment value: {value}")
        if not force and not self._buttons[value].isEnabled():
            return
        changed = value != self._value
        self._value = value
        self._buttons[value].setChecked(True)
        if emit and changed:
            self.value_changed.emit(value)

    def set_option_enabled(self, value: str, enabled: bool) -> None:
        button = self._buttons[value]
        button.setEnabled(enabled)
        if not enabled and self._value == value:
            for candidate, candidate_button in self._buttons.items():
                if candidate_button.isEnabled():
                    self.set_value(candidate, emit=True)
                    return

    def button(self, value: str) -> QPushButton:
        return self._buttons[value]

    def _clear(self) -> None:
        for button in self._buttons.values():
            self._group.removeButton(button)
            self._layout.removeWidget(button)
            button.setParent(None)
        self._buttons.clear()
        self._value = ""
