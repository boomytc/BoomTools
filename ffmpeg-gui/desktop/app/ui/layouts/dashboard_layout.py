from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QResizeEvent, QShowEvent
from PySide6.QtWidgets import QSplitter, QSizePolicy, QVBoxLayout, QWidget

from desktop.app.ui.panels import CommandPreviewPanel, MediaPreviewPanel, OperationPanel, RuntimePanel, TaskPanel
from desktop.app.ui.panels.task_panel import TASK_PANEL_DEFAULT_MIN_HEIGHT


class DashboardLayout(QWidget):
    def __init__(
        self,
        *,
        runtime_panel: RuntimePanel,
        operation_panel: OperationPanel,
        command_preview_panel: CommandPreviewPanel,
        media_preview_panel: MediaPreviewPanel,
        task_panel: TaskPanel,
    ) -> None:
        super().__init__()
        self.setObjectName("dashboardLayoutHost")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.runtime_panel = runtime_panel
        self.operation_panel = operation_panel
        self.command_preview_panel = command_preview_panel
        self.media_preview_panel = media_preview_panel
        self.task_panel = task_panel
        self._assign_panel_ids()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.runtime_panel)

        self.workflow_host = QWidget()
        self.workflow_host.setObjectName("workflowHost")
        workflow_layout = QVBoxLayout(self.workflow_host)
        workflow_layout.setContentsMargins(0, 0, 0, 0)
        workflow_layout.setSpacing(8)

        self.workflow_splitter = QSplitter(Qt.Orientation.Vertical)
        self.workflow_splitter.setObjectName("workflowSplitter")
        self.workflow_splitter.setChildrenCollapsible(False)
        self.workflow_splitter.addWidget(self.operation_panel)
        self.workflow_splitter.addWidget(self.task_panel)
        self.workflow_splitter.setStretchFactor(0, 0)
        self.workflow_splitter.setStretchFactor(1, 1)
        workflow_layout.addWidget(self.workflow_splitter, 1)
        self.operation_panel.minimum_height_changed.connect(self.sync_workflow_splitter)
        self.sync_workflow_splitter()

        self.content_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.content_splitter.setObjectName("contentSplitter")
        self.content_splitter.setChildrenCollapsible(False)
        self.content_splitter.addWidget(self.workflow_host)
        self.content_splitter.addWidget(self.media_preview_panel)
        self.content_splitter.setStretchFactor(0, 5)
        self.content_splitter.setStretchFactor(1, 2)
        self.content_splitter.setSizes([860, 420])
        layout.addWidget(self.content_splitter, 1)

    def sync_workflow_splitter(self) -> None:
        operation_height = self.operation_panel.minimumHeight()
        available_height = self.workflow_splitter.height() - self.workflow_splitter.handleWidth()
        use_dense_tasks = available_height > 0 and operation_height + TASK_PANEL_DEFAULT_MIN_HEIGHT > available_height
        self.task_panel.set_dense_mode(use_dense_tasks)
        task_minimum = self.task_panel.minimumHeight()

        current_sizes = self.workflow_splitter.sizes()
        total_height = available_height if available_height > 0 else sum(current_sizes)
        if total_height <= 0:
            total_height = operation_height + max(420, task_minimum)
        operation_height = min(operation_height, max(self.operation_panel.minimumHeight(), total_height - task_minimum))
        task_height = max(self.task_panel.minimumHeight(), total_height - operation_height)
        self.workflow_splitter.setSizes([operation_height, task_height])

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.sync_workflow_splitter()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self.sync_workflow_splitter)

    def _assign_panel_ids(self) -> None:
        self.runtime_panel.setProperty("panel_id", "content")
        self.operation_panel.operation_form.operation_selector.setProperty("panel_id", "operation")
        self.operation_panel.operation_form.parameter_form.setProperty("panel_id", "parameters")
        self.operation_panel.stack_panel.setProperty("panel_id", "stack")
        self.command_preview_panel.setProperty("panel_id", "command_preview")
        self.media_preview_panel.setProperty("panel_id", "media_preview")
        self.task_panel.setProperty("panel_id", "tasks")
