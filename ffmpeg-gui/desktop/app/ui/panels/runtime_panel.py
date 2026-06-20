from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
)

from desktop.app.ui.widgets.path_picker import PathPicker
from shared.contracts import MediaInfo


class RuntimePanel(QFrame):
    input_browse_requested = Signal()
    input_path_dropped = Signal(str)
    input_mode_changed = Signal(bool)
    batch_files_requested = Signal()
    batch_paths_dropped = Signal(list)
    batch_files_cleared = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._batch_mode = False
        self._batch_paths: list[Path] = []
        self._busy = False
        self.setObjectName("runtimePanel")
        self.setAcceptDrops(True)
        self.setMinimumHeight(180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        title_label = QLabel("输入媒体")
        title_label.setObjectName("sectionTitle")
        header_row.addWidget(title_label)
        header_row.addStretch(1)
        self.single_input_button = QPushButton("单个文件")
        self.batch_input_button = QPushButton("批量文件")
        self.input_mode_group = QButtonGroup(self)
        self.input_mode_group.setExclusive(True)
        for button in (self.single_input_button, self.batch_input_button):
            button.setCheckable(True)
            button.setProperty("role", "segmentButton")
            self.input_mode_group.addButton(button)
            header_row.addWidget(button)
        self.single_input_button.setChecked(True)
        self.single_input_button.clicked.connect(lambda _checked=False: self.set_batch_input_mode(False))
        self.batch_input_button.clicked.connect(lambda _checked=False: self.set_batch_input_mode(True))
        layout.addLayout(header_row)

        self.input_path_picker = PathPicker(placeholder="选择本机媒体文件", button_text="选择文件")
        self.input_path_picker.browse_requested.connect(self.input_browse_requested.emit)

        self.input_stack = QStackedWidget()
        self.input_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.single_input_page = self._create_single_input_page()
        self.batch_input_page = self._create_batch_input_page()
        self.input_stack.addWidget(self.single_input_page)
        self.input_stack.addWidget(self.batch_input_page)
        self.input_stack.setFixedHeight(142)
        layout.addWidget(self.input_stack)

        layout.addStretch(1)

    def selected_input_path(self) -> Path | None:
        return self.input_path_picker.path()

    def selected_batch_paths(self) -> list[Path]:
        return list(self._batch_paths)

    def batch_input_mode(self) -> bool:
        return self._batch_mode

    def input_path_text(self) -> str:
        return self.input_path_picker.text()

    def set_input_path_text(self, path: str) -> None:
        self.input_path_picker.set_text(str(path))

    def set_media_info(self, media_info: MediaInfo | None) -> None:
        return

    def set_batch_progress(self, current: int, total: int) -> None:
        if total == 0:
            if self._batch_paths:
                self.batch_progress_label.setText(f"已选择 {len(self._batch_paths)} 个文件")
            else:
                self.batch_progress_label.setText("未选择文件")
            return
        if current >= total:
            self.batch_progress_label.setText(f"处理完成：{total}/{total}")
            return
        if current == 0:
            self.batch_progress_label.setText(f"已选择 {total} 个文件")
            return
        self.batch_progress_label.setText(f"处理进度：{current}/{total}")

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        enabled = not busy
        self.single_input_button.setEnabled(enabled)
        self.batch_input_button.setEnabled(enabled)
        self.input_path_picker.set_enabled(enabled)
        self.batch_choose_button.setEnabled(enabled)
        self.batch_clear_button.setEnabled(enabled and bool(self._batch_paths))

    def set_batch_add_enabled(self, enabled: bool) -> None:
        self.batch_choose_button.setEnabled(enabled and not self._busy)

    def set_batch_input_mode(self, enabled: bool, *, emit: bool = True) -> None:
        if self._batch_mode == enabled:
            self._sync_input_mode()
            return
        self._batch_mode = enabled
        self._sync_input_mode()
        if emit:
            self.input_mode_changed.emit(enabled)

    def set_batch_paths(self, paths: list[str | Path]) -> None:
        self._batch_paths = self._normalize_paths(paths)
        self._refresh_batch_list()
        self.set_batch_progress(0, len(self._batch_paths))

    def clear_batch_paths(self, *, emit: bool = False) -> None:
        self._batch_paths = []
        self._refresh_batch_list()
        self.set_batch_progress(0, 0)
        if emit:
            self.batch_files_cleared.emit()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if not self._busy and event.mimeData().hasUrls():
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
        if self._batch_mode:
            self.set_batch_paths(paths)
            self.batch_paths_dropped.emit([str(path) for path in self._batch_paths])
            event.acceptProposedAction()
            return
        path = paths[0]
        self.input_path_picker.set_text(str(path))
        self.input_path_dropped.emit(str(path))
        event.acceptProposedAction()

    def _create_single_input_page(self) -> QFrame:
        drop_area = QFrame()
        drop_area.setObjectName("fileDropArea")
        drop_area.setMinimumHeight(136)
        drop_area.setMaximumHeight(142)
        drop_layout = QVBoxLayout(drop_area)
        drop_layout.setContentsMargins(14, 12, 14, 12)
        drop_layout.setSpacing(8)
        drop_title = QLabel("选择或拖入本机视频/音频文件")
        drop_title.setObjectName("dropTitle")
        drop_hint = QLabel("MP4、WebM、MOV、AVI、MKV、GIF 等；文件只在本机处理。")
        drop_hint.setObjectName("mutedLabel")
        drop_layout.addWidget(drop_title)
        drop_layout.addWidget(drop_hint)
        drop_layout.addWidget(self.input_path_picker)
        drop_layout.addStretch(1)
        return drop_area

    def _create_batch_input_page(self) -> QFrame:
        drop_area = QFrame()
        drop_area.setObjectName("fileDropArea")
        drop_area.setMinimumHeight(218)
        drop_area.setMaximumHeight(236)
        drop_layout = QVBoxLayout(drop_area)
        drop_layout.setContentsMargins(12, 12, 12, 12)
        drop_layout.setSpacing(8)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        drop_title = QLabel("选择或拖入多个本机媒体文件")
        drop_title.setObjectName("dropTitle")
        self.batch_progress_label = QLabel("未选择文件")
        self.batch_progress_label.setObjectName("batchProgressLabel")
        title_row.addWidget(drop_title)
        title_row.addStretch(1)
        title_row.addWidget(self.batch_progress_label)

        drop_hint = QLabel("批量模式会对每个文件执行同一套处理参数；仅支持可批量执行的动作。")
        drop_hint.setObjectName("mutedLabel")

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self.batch_choose_button = QPushButton("选择多个文件")
        self.batch_choose_button.setProperty("role", "quiet")
        self.batch_choose_button.clicked.connect(lambda _checked=False: self.batch_files_requested.emit())
        self.batch_clear_button = QPushButton("清空")
        self.batch_clear_button.setProperty("role", "quiet")
        self.batch_clear_button.setEnabled(False)
        self.batch_clear_button.clicked.connect(lambda _checked=False: self.clear_batch_paths(emit=True))
        action_row.addWidget(self.batch_choose_button)
        action_row.addWidget(self.batch_clear_button)
        action_row.addStretch(1)

        self.batch_file_list = QListWidget()
        self.batch_file_list.setObjectName("batchFileList")
        self.batch_file_list.setMinimumHeight(86)
        self.batch_file_list.setMaximumHeight(120)

        drop_layout.addLayout(title_row)
        drop_layout.addWidget(drop_hint)
        drop_layout.addLayout(action_row)
        drop_layout.addWidget(self.batch_file_list)
        return drop_area

    def _sync_input_mode(self) -> None:
        self.single_input_button.setChecked(not self._batch_mode)
        self.batch_input_button.setChecked(self._batch_mode)
        self.input_stack.setCurrentWidget(self.batch_input_page if self._batch_mode else self.single_input_page)
        self.input_stack.setFixedHeight(236 if self._batch_mode else 142)

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

    def _refresh_batch_list(self) -> None:
        self.batch_file_list.clear()
        for path in self._batch_paths:
            item = QListWidgetItem(path.name or str(path))
            item.setToolTip(str(path))
            self.batch_file_list.addItem(item)
        self.batch_clear_button.setEnabled(not self._busy and bool(self._batch_paths))
