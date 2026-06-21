from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget


class FormSection(QWidget):
    def __init__(self, title: str, *, empty_text: str = "", field_max_width: int = 560) -> None:
        super().__init__()
        self.setObjectName("formSection")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self._field_max_width = field_max_width

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("formSectionLabel")
        layout.addWidget(self.title_label)

        self.form_layout = QFormLayout()
        self.form_layout.setContentsMargins(0, 0, 0, 0)
        self.form_layout.setHorizontalSpacing(10)
        self.form_layout.setVerticalSpacing(6)
        self.form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        layout.addLayout(self.form_layout)

        self.empty_label = QLabel(empty_text)
        self.empty_label.setObjectName("mutedLabel")
        self.empty_label.setVisible(bool(empty_text))
        layout.addWidget(self.empty_label)

    def add_row(self, label: str, field: QWidget) -> None:
        field.setMaximumWidth(self._field_max_width)
        self.empty_label.setVisible(False)
        self.form_layout.addRow(label, field)

    def clear(self) -> None:
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        self.empty_label.setVisible(bool(self.empty_label.text()))

    def set_empty_text(self, text: str) -> None:
        self.empty_label.setText(text)
        self.empty_label.setVisible(bool(text) and self.form_layout.rowCount() == 0)
