from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionViewItem, QStyledItemDelegate

from desktop.app.ui.widgets.task_table_model import ACTION_ENABLED_ROLE, MEDIA_SUMMARY_ROLE, PROGRESS_ROLE, STATUS_ROLE
from shared.contracts import TaskStatus


STATUS_STYLES: dict[str, tuple[str, str, str]] = {
    TaskStatus.probing.value: ("读取中", "#3b3218", "#ffd166"),
    TaskStatus.ready.value: ("就绪", "#173527", "#73e0a3"),
    TaskStatus.pending.value: ("待处理", "#3b3218", "#ffd166"),
    TaskStatus.running.value: ("运行中", "#17365f", "#8fbdff"),
    TaskStatus.succeeded.value: ("完成", "#153b2a", "#64d691"),
    TaskStatus.failed.value: ("失败", "#4a1f28", "#ff8a9a"),
    TaskStatus.cancelled.value: ("取消", "#2b303d", "#a7b0c2"),
}


class ProgressBarDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:  # type: ignore[override]
        progress = index.data(PROGRESS_ROLE)
        status = index.data(STATUS_ROLE)

        painter.save()
        self._draw_item_background(painter, option, index)
        self._draw_progress(painter, option.rect, progress, status)
        painter.restore()

    def _draw_progress(self, painter: QPainter, rect: QRect, progress: object, status: object) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        bar_rect = rect.adjusted(10, 8, -10, -8)
        bar_rect.setHeight(max(16, min(22, bar_rect.height())))
        bar_rect.moveTop(rect.y() + (rect.height() - bar_rect.height()) // 2)

        status_value = status.value if isinstance(status, TaskStatus) else str(status or "")
        if status_value and status_value != TaskStatus.running.value:
            label, background, foreground = STATUS_STYLES.get(status_value, (status_value, "#2b303d", "#a7b0c2"))
            painter.setPen(QPen(QColor("#4a536a")))
            painter.setBrush(QColor(background))
            painter.drawRoundedRect(bar_rect, 6, 6)
            painter.setPen(QPen(QColor(foreground)))
            painter.drawText(bar_rect, Qt.AlignmentFlag.AlignCenter, label)
            return

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#22283a"))
        painter.drawRoundedRect(bar_rect, 6, 6)

        if isinstance(progress, (int, float)):
            bounded = max(0.0, min(float(progress), 1.0))
            fill_rect = QRect(bar_rect)
            fill_rect.setWidth(max(4, int(bar_rect.width() * bounded)))
            painter.setBrush(QColor("#4f83ff"))
            painter.drawRoundedRect(fill_rect, 6, 6)
            text = f"{int(bounded * 100)}%"
            text_color = QColor("#dbe7ff")
        else:
            painter.setBrush(QColor("#2c518b"))
            marker_width = max(28, bar_rect.width() // 3)
            marker_rect = QRect(bar_rect.x(), bar_rect.y(), marker_width, bar_rect.height())
            painter.drawRoundedRect(marker_rect, 6, 6)
            text = "运行中"
            text_color = QColor("#8fbdff")

        painter.setPen(QPen(text_color))
        painter.drawText(bar_rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_item_background(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        QApplication.style().drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter)


class FileSummaryDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:  # type: ignore[override]
        tags = index.data(MEDIA_SUMMARY_ROLE) or []
        if not isinstance(tags, list):
            tags = []
        title = str(index.data() or "")

        painter.save()
        self._draw_item_background(painter, option, index)
        self._draw_title(painter, option.rect, title)
        self._draw_tags(painter, option.rect, [str(tag) for tag in tags])
        painter.restore()

    def _draw_title(self, painter: QPainter, rect: QRect, title: str) -> None:
        text_rect = rect.adjusted(10, 6, -10, -26)
        metrics = painter.fontMetrics()
        text = metrics.elidedText(title, Qt.TextElideMode.ElideRight, max(24, text_rect.width()))
        painter.setPen(QPen(QColor("#d7e2f5")))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)

    def _draw_tags(self, painter: QPainter, rect: QRect, tags: list[str]) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        tag_font = painter.font()
        tag_font.setPointSize(max(9, tag_font.pointSize() - 2))
        painter.setFont(tag_font)
        metrics = painter.fontMetrics()
        x = rect.x() + 10
        y = rect.bottom() - 21
        max_x = rect.right() - 10

        for index, tag in enumerate(tags):
            chip_width = min(max(30, metrics.horizontalAdvance(tag) + 12), 72)
            if x + chip_width > max_x:
                remaining = len(tags) - index
                if remaining > 0 and x + 34 <= max_x:
                    self._draw_chip(painter, QRect(x, y, 32, 18), f"+{remaining}", error=False)
                return
            self._draw_chip(painter, QRect(x, y, chip_width, 18), tag, error=tag == "读取失败")
            x += chip_width + 4

    def _draw_chip(self, painter: QPainter, rect: QRect, text: str, *, error: bool) -> None:
        if error:
            background = QColor("#3a2028")
            foreground = QColor("#ff8a9a")
            border = QColor("#74404a")
        else:
            background = QColor("#202638")
            foreground = QColor("#cfe0ff")
            border = QColor("#4a536a")

        painter.setPen(QPen(border))
        painter.setBrush(background)
        painter.drawRoundedRect(rect, 5, 5)
        painter.setPen(QPen(foreground))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_item_background(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        QApplication.style().drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter)


MediaSummaryDelegate = FileSummaryDelegate


class RemoveActionDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:  # type: ignore[override]
        enabled = bool(index.data(ACTION_ENABLED_ROLE))
        label = str(index.data() or "移除")

        painter.save()
        self._draw_item_background(painter, option, index)
        self._draw_button(painter, option.rect, label, enabled=enabled)
        painter.restore()

    def _draw_button(self, painter: QPainter, rect: QRect, text: str, *, enabled: bool) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        button_width = min(54, max(38, rect.width() - 16))
        button_height = min(22, max(18, rect.height() - 14))
        button_rect = QRect(
            rect.x() + (rect.width() - button_width) // 2,
            rect.y() + (rect.height() - button_height) // 2,
            button_width,
            button_height,
        )
        if enabled:
            background = QColor("#202638")
            foreground = QColor("#d8e0ef")
            border = QColor("#4a536a")
        else:
            background = QColor("#171b26")
            foreground = QColor("#687386")
            border = QColor("#30364a")

        painter.setPen(QPen(border))
        painter.setBrush(background)
        painter.drawRoundedRect(button_rect, 5, 5)
        painter.setPen(QPen(foreground))
        painter.drawText(button_rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_item_background(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        QApplication.style().drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter)
