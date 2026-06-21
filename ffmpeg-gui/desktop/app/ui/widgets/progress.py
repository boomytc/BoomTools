from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QWidget

from shared.contracts import TaskStatus


@dataclass(frozen=True)
class StatusProgressVisual:
    label: str
    background: str
    foreground: str
    border: str


@dataclass(frozen=True)
class ProgressVisualSpec:
    track: str = "#22283a"
    fill: str = "#4f83ff"
    indeterminate_fill: str = "#2c518b"
    text: str = "#dbe7ff"
    indeterminate_text: str = "#8fbdff"
    status_border: str = "#4a536a"
    unknown_status_background: str = "#2b303d"
    unknown_status_foreground: str = "#a7b0c2"
    radius: int = 6
    horizontal_margin: int = 10
    vertical_margin: int = 8
    min_height: int = 16
    max_height: int = 22
    min_fill_width: int = 4
    min_marker_width: int = 28
    marker_divisor: int = 3


DEFAULT_PROGRESS_SPEC = ProgressVisualSpec()

STATUS_PROGRESS_VISUALS: dict[str, StatusProgressVisual] = {
    TaskStatus.probing.value: StatusProgressVisual("读取中", "#3b3218", "#ffd166", DEFAULT_PROGRESS_SPEC.status_border),
    TaskStatus.ready.value: StatusProgressVisual("就绪", "#173527", "#73e0a3", DEFAULT_PROGRESS_SPEC.status_border),
    TaskStatus.pending.value: StatusProgressVisual("待处理", "#3b3218", "#ffd166", DEFAULT_PROGRESS_SPEC.status_border),
    TaskStatus.succeeded.value: StatusProgressVisual("完成", "#153b2a", "#64d691", DEFAULT_PROGRESS_SPEC.status_border),
    TaskStatus.failed.value: StatusProgressVisual("失败", "#4a1f28", "#ff8a9a", DEFAULT_PROGRESS_SPEC.status_border),
    TaskStatus.cancelled.value: StatusProgressVisual("取消", "#2b303d", "#a7b0c2", DEFAULT_PROGRESS_SPEC.status_border),
}


def progress_bar_rect(cell_rect: QRect, spec: ProgressVisualSpec = DEFAULT_PROGRESS_SPEC) -> QRect:
    bar_rect = cell_rect.adjusted(
        spec.horizontal_margin,
        spec.vertical_margin,
        -spec.horizontal_margin,
        -spec.vertical_margin,
    )
    bar_rect.setHeight(max(spec.min_height, min(spec.max_height, bar_rect.height())))
    bar_rect.moveTop(cell_rect.y() + (cell_rect.height() - bar_rect.height()) // 2)
    return bar_rect


def status_progress_visual(
    status: object,
    spec: ProgressVisualSpec = DEFAULT_PROGRESS_SPEC,
) -> StatusProgressVisual | None:
    status_value = status.value if isinstance(status, TaskStatus) else str(status or "")
    if not status_value or status_value == TaskStatus.running.value:
        return None
    return STATUS_PROGRESS_VISUALS.get(
        status_value,
        StatusProgressVisual(
            status_value,
            spec.unknown_status_background,
            spec.unknown_status_foreground,
            spec.status_border,
        ),
    )


class ProgressSummaryWidget(QWidget):
    def __init__(
        self,
        *,
        label_object_name: str = "totalProgressLabel",
        bar_object_name: str = "totalProgressBar",
        bar_width: int | None = 132,
    ) -> None:
        super().__init__()
        self.setObjectName("progressSummaryWidget")
        self.setProperty("role", "progressSummary")
        self.setProperty("state", "empty")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.label = QLabel("无任务")
        self.label.setObjectName(label_object_name)
        self.label.setProperty("state", "empty")

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName(bar_object_name)
        self.progress_bar.setProperty("variant", "compact")
        self.progress_bar.setProperty("state", "empty")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        if bar_width is not None:
            self.progress_bar.setFixedWidth(bar_width)

        layout.addWidget(self.label)
        layout.addWidget(self.progress_bar)
        layout.addStretch(1)

    def set_summary(
        self,
        *,
        label: str,
        tooltip: str,
        percent: int,
        indeterminate: bool = False,
        state: str = "active",
    ) -> None:
        if indeterminate:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(max(0, min(percent, 100)))

        self.label.setText(label)
        self.label.setToolTip(tooltip)
        self.progress_bar.setToolTip(tooltip)
        self._set_state(state)

    def _set_state(self, state: str) -> None:
        for widget in (self, self.label, self.progress_bar):
            widget.setProperty("state", state)
            style = widget.style()
            style.unpolish(widget)
            style.polish(widget)
            widget.update()
