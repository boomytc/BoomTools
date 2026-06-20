from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QTableView, QVBoxLayout

from desktop.app.ui.delegates import MediaSummaryDelegate, ProgressBarDelegate, StatusBadgeDelegate
from desktop.app.ui.widgets.task_table_model import TaskTableModel


class TaskPanel(QGroupBox):
    def __init__(self, task_model: TaskTableModel) -> None:
        super().__init__("任务队列")
        self.setObjectName("taskPanel")
        self.setMinimumHeight(156)
        self.setMaximumHeight(190)
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
        self.task_table.setItemDelegateForColumn(2, MediaSummaryDelegate(self.task_table))
        self.task_table.setItemDelegateForColumn(5, ProgressBarDelegate(self.task_table))
        self.task_table.resizeColumnsToContents()
        self.task_table.setColumnWidth(0, 86)
        self.task_table.setColumnWidth(1, 170)
        self.task_table.setColumnWidth(2, 280)
        self.task_table.setColumnWidth(3, 130)
        self.task_table.setColumnWidth(4, 130)
        self.task_table.setColumnWidth(5, 120)
        self.task_table.setMinimumHeight(112)
        layout.addWidget(self.task_table)
