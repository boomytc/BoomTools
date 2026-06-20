from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QKeyEvent, QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from shared.contracts import MediaInfo


class MediaDropArea(QFrame):
    clicked = Signal()
    paths_dropped = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("fileDropArea")
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName("选择或拖入本机视频/音频文件")
        self.setToolTip("点击选择本机媒体文件，或拖入文件")

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if (
            self.isEnabled()
            and event.button() == Qt.MouseButton.LeftButton
            and self.rect().contains(event.position().toPoint())
        ):
            self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self.isEnabled() and event.key() in (
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
            Qt.Key.Key_Space,
        ):
            self.clicked.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self.isEnabled() and event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        paths = [url.toLocalFile() for url in urls if url.toLocalFile()]
        if self.isEnabled() and paths:
            self.paths_dropped.emit(paths)
            event.acceptProposedAction()
            return
        super().dropEvent(event)


class RuntimePanel(QFrame):
    input_browse_requested = Signal()
    input_path_dropped = Signal(str)
    input_mode_changed = Signal(bool)
    batch_files_requested = Signal()
    batch_paths_dropped = Signal(list)
    batch_files_cleared = Signal()
    output_dir_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._batch_paths: list[Path] = []
        self._last_input_dir: Path | None = None
        self._output_dir_path: Path | None = None
        self._input_add_enabled = True
        self._busy = False
        self.setObjectName("runtimePanel")
        self.setAcceptDrops(True)
        self.setMinimumHeight(136)
        self.setMaximumHeight(158)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        title_label = QLabel("内容选择")
        title_label.setObjectName("sectionTitle")
        header_row.addWidget(title_label)
        header_row.addStretch(1)
        layout.addLayout(header_row)

        self.drop_area = self._create_input_area()
        layout.addWidget(self.drop_area)

        output_row = QHBoxLayout()
        output_row.setSpacing(8)
        self.output_dir_value = QLabel("目标目录：未选择输出目录")
        self.output_dir_value.setObjectName("outputDirSummary")
        self.output_dir_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.output_dir_value.setToolTip("未选择输出目录")
        self.output_dir_value.setMinimumWidth(0)
        output_row.addWidget(self.output_dir_value, 1)
        self.output_dir_button = QPushButton("输出目录选择")
        self.output_dir_button.setProperty("role", "quiet")
        self.output_dir_button.clicked.connect(lambda _checked=False: self.output_dir_requested.emit())
        output_row.addWidget(self.output_dir_button)
        layout.addLayout(output_row)

    def selected_input_path(self) -> Path | None:
        return self._batch_paths[0] if self._batch_paths else None

    def selected_output_dir(self) -> Path | None:
        return self._output_dir_path

    def selected_batch_paths(self) -> list[Path]:
        return list(self._batch_paths)

    def batch_input_mode(self) -> bool:
        return len(self._batch_paths) > 1

    def input_path_text(self) -> str:
        return str(self._last_input_dir or "")

    def set_input_path_text(self, path: str) -> None:
        normalized = Path(path)
        self._batch_paths = [normalized] if path else []
        self._last_input_dir = normalized.parent if path else None
        self._sync_selection_summary()

    def set_output_dir_text(self, path: str) -> None:
        normalized = path.strip()
        self._output_dir_path = Path(normalized) if normalized else None
        display_text = f"目标目录：{normalized}" if normalized else "目标目录：未选择输出目录"
        self.output_dir_value.setText(display_text)
        self.output_dir_value.setToolTip(normalized or "未选择输出目录")

    def set_media_info(self, media_info: MediaInfo | None) -> None:
        return

    def set_batch_progress(self, current: int, total: int) -> None:
        if total == 0 or current == 0:
            self._sync_selection_summary()
            return
        if current >= total:
            self.selection_summary.setText(f"处理完成：{total}/{total}")
            return
        self.selection_summary.setText(f"处理进度：{current}/{total}")

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._sync_input_add_enabled()
        self.output_dir_button.setEnabled(not busy)

    def set_batch_add_enabled(self, enabled: bool) -> None:
        self._input_add_enabled = enabled
        self._sync_input_add_enabled()

    def set_batch_input_mode(self, enabled: bool, *, emit: bool = True) -> None:
        if emit:
            self.input_mode_changed.emit(enabled)

    def set_batch_paths(self, paths: list[str | Path]) -> None:
        self._batch_paths = self._normalize_paths(paths)
        if self._batch_paths:
            self._last_input_dir = self._batch_paths[-1].parent
        self._sync_selection_summary()

    def clear_batch_paths(self, *, emit: bool = False) -> None:
        self._batch_paths = []
        self._sync_selection_summary()
        self.set_batch_progress(0, 0)
        if emit:
            self.batch_files_cleared.emit()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._can_add_inputs() and event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if not urls:
            super().dropEvent(event)
            return
        paths = [Path(url.toLocalFile()) for url in urls if url.toLocalFile()]
        if not paths:
            super().dropEvent(event)
            return
        self._set_dropped_paths(paths)
        event.acceptProposedAction()

    def _create_input_area(self) -> MediaDropArea:
        drop_area = MediaDropArea()
        drop_area.setMinimumHeight(64)
        drop_area.setMaximumHeight(72)
        drop_area.clicked.connect(lambda: self.batch_files_requested.emit())
        drop_area.paths_dropped.connect(self._set_dropped_paths)
        drop_layout = QVBoxLayout(drop_area)
        drop_layout.setContentsMargins(14, 7, 14, 7)
        drop_layout.setSpacing(4)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        drop_title = QLabel("点击选择或拖入本机视频/音频文件")
        drop_title.setObjectName("dropTitle")
        self.selection_summary = QLabel("未选择文件")
        self.selection_summary.setObjectName("batchProgressLabel")
        drop_title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.selection_summary.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        title_row.addWidget(drop_title)
        title_row.addStretch(1)
        title_row.addWidget(self.selection_summary)

        drop_hint = QLabel("可一次选择多个文件；新文件会追加到任务队列，文件只在本机处理。")
        drop_hint.setObjectName("mutedLabel")
        drop_hint.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        drop_layout.addLayout(title_row)
        drop_layout.addWidget(drop_hint)
        return drop_area

    def _set_dropped_paths(self, paths: list[str | Path]) -> None:
        if not self._can_add_inputs():
            return
        self.set_batch_paths(paths)
        self.batch_paths_dropped.emit([str(path) for path in self._batch_paths])

    def _can_add_inputs(self) -> bool:
        return self._input_add_enabled and not self._busy

    def _sync_input_add_enabled(self) -> None:
        can_add = self._can_add_inputs()
        self.drop_area.setEnabled(can_add)
        self.drop_area.setCursor(Qt.CursorShape.PointingHandCursor if can_add else Qt.CursorShape.ArrowCursor)

    def _normalize_paths(self, paths: list[str | Path]) -> list[Path]:
        normalized: list[Path] = []
        seen: set[str] = set()
        for raw_path in paths:
            path = Path(raw_path)
            key = str(path)
            if not key or key in seen:
                continue
            seen.add(key)
            normalized.append(path)
        return normalized

    def _sync_selection_summary(self) -> None:
        count = len(self._batch_paths)
        if count == 0:
            self.selection_summary.setText("未选择文件")
        elif count == 1:
            self.selection_summary.setText("已添加 1 个文件")
        else:
            self.selection_summary.setText(f"已添加 {count} 个文件")
