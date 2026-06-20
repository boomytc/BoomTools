from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QTableView, QVBoxLayout

from desktop.app.ui.delegates import ProgressBarDelegate, StatusBadgeDelegate
from desktop.app.ui.widgets.task_table_model import TaskTableModel


class TaskPanel(QGroupBox):
    def __init__(self, task_model: TaskTableModel) -> None:
        super().__init__("任务队列")
        self.setObjectName("taskPanel")
        self.setMinimumHeight(132)
        self.setMaximumHeight(150)
        layout = QVBoxLayout(self)
        self.task_table = QTableView()
        self.task_table.setObjectName("taskTable")
        self.task_table.setModel(task_model)
        self.task_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.horizontalHeader().setStretchLastSection(True)
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.verticalHeader().setDefaultSectionSize(38)
        self.task_table.setShowGrid(False)
        self.task_table.setSortingEnabled(False)
        self.task_table.setItemDelegateForColumn(0, StatusBadgeDelegate(self.task_table))
        self.task_table.setItemDelegateForColumn(4, ProgressBarDelegate(self.task_table))
        self.task_table.resizeColumnsToContents()
        self.task_table.setColumnWidth(0, 92)
        self.task_table.setColumnWidth(1, 160)
        self.task_table.setColumnWidth(4, 120)
        self.task_table.setMinimumHeight(92)
        layout.addWidget(self.task_table)
