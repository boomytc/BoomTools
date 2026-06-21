from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionViewItem, QStyledItemDelegate

from desktop.app.ui.widgets.progress import DEFAULT_PROGRESS_SPEC, progress_bar_rect, status_progress_visual
from desktop.app.ui.widgets.task_table_model import ACTION_ENABLED_ROLE, MEDIA_SUMMARY_ROLE, PROGRESS_ROLE, STATUS_ROLE


class ProgressBarDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:  # type: ignore[override]
        progress = index.data(PROGRESS_ROLE)
        status = index.data(STATUS_ROLE)

        painter.save()
        self._draw_item_background(painter, option, index)
        self._draw_progress(painter, option.rect, progress, status)
        painter.restore()

    def _draw_progress(self, painter: QPainter, rect: QRect, progress: object, status: object) -> None:
        spec = DEFAULT_PROGRESS_SPEC
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        bar_rect = progress_bar_rect(rect, spec)

        status_visual = status_progress_visual(status, spec)
        if status_visual is not None:
            painter.setPen(QPen(QColor(status_visual.border)))
            painter.setBrush(QColor(status_visual.background))
            painter.drawRoundedRect(bar_rect, spec.radius, spec.radius)
            painter.setPen(QPen(QColor(status_visual.foreground)))
            painter.drawText(bar_rect, Qt.AlignmentFlag.AlignCenter, status_visual.label)
            return

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(spec.track))
        painter.drawRoundedRect(bar_rect, spec.radius, spec.radius)

        if isinstance(progress, (int, float)):
            bounded = max(0.0, min(float(progress), 1.0))
            fill_rect = QRect(bar_rect)
            fill_rect.setWidth(max(spec.min_fill_width, int(bar_rect.width() * bounded)))
            painter.setBrush(QColor(spec.fill))
            painter.drawRoundedRect(fill_rect, spec.radius, spec.radius)
            text = f"{int(bounded * 100)}%"
            text_color = QColor(spec.text)
        else:
            painter.setBrush(QColor(spec.indeterminate_fill))
            marker_width = max(spec.min_marker_width, bar_rect.width() // spec.marker_divisor)
            marker_rect = QRect(bar_rect.x(), bar_rect.y(), marker_width, bar_rect.height())
            painter.drawRoundedRect(marker_rect, spec.radius, spec.radius)
            text = "运行中"
            text_color = QColor(spec.indeterminate_text)

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


class TextCellDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:  # type: ignore[override]
        text = str(index.data() or "")

        painter.save()
        self._draw_item_background(painter, option, index)
        self._draw_text(painter, option, text)
        painter.restore()

    def _draw_text(self, painter: QPainter, option: QStyleOptionViewItem, text: str) -> None:
        text_rect = option.rect.adjusted(10, 0, -10, 0)
        metrics = painter.fontMetrics()
        elided_text = metrics.elidedText(text, Qt.TextElideMode.ElideRight, max(24, text_rect.width()))
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        painter.setPen(QPen(QColor("#ffffff" if selected else "#d7e2f5")))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_text)

    def _draw_item_background(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        QApplication.style().drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter)


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
