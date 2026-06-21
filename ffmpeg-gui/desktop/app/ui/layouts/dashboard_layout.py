from __future__ import annotations

from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from desktop.app.ui.panels import CommandPreviewPanel, OperationPanel, RuntimePanel, TaskPanel


class DashboardLayout(QWidget):
    def __init__(
        self,
        *,
        runtime_panel: RuntimePanel,
        operation_panel: OperationPanel,
        command_preview_panel: CommandPreviewPanel,
        task_panel: TaskPanel,
    ) -> None:
        super().__init__()
        self.setObjectName("dashboardLayoutHost")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.runtime_panel = runtime_panel
        self.operation_panel = operation_panel
        self.command_preview_panel = command_preview_panel
        self.task_panel = task_panel
        self._assign_panel_ids()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.runtime_panel)
        layout.addWidget(self.operation_panel)
        layout.addWidget(self.command_preview_panel)
        layout.addWidget(self.task_panel, 1)

    def _assign_panel_ids(self) -> None:
        self.runtime_panel.setProperty("panel_id", "content")
        self.operation_panel.operation_form.operation_selector.setProperty("panel_id", "operation")
        self.operation_panel.operation_form.parameter_form.setProperty("panel_id", "parameters")
        self.operation_panel.stack_panel.setProperty("panel_id", "stack")
        self.command_preview_panel.setProperty("panel_id", "command_preview")
        self.task_panel.setProperty("panel_id", "tasks")
