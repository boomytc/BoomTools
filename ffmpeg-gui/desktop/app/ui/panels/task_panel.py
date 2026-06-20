from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QTableView, QVBoxLayout

from desktop.app.ui.widgets.task_table_model import TaskTableModel


class TaskPanel(QGroupBox):
    def __init__(self, task_model: TaskTableModel) -> None:
        super().__init__("任务")
        layout = QVBoxLayout(self)
        self.task_table = QTableView()
        self.task_table.setModel(task_model)
        self.task_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.horizontalHeader().setStretchLastSection(True)
        self.task_table.resizeColumnsToContents()
        layout.addWidget(self.task_table)
