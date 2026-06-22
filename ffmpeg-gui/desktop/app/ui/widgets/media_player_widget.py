from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QSize, QUrl, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap, QPolygonF
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

MEDIA_ICON_SIZE = QSize(18, 18)
MEDIA_ICON_COLOR = QColor("#f4f7fb")
MEDIA_ICON_DISABLED_COLOR = QColor("#687386")


class MediaPlayerWidget(QWidget):
    position_seconds_changed = Signal(float)
    duration_seconds_changed = Signal(float)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("mediaPlayerWidget")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._path: Path | None = None
        self._fallback_duration_ms = 0
        self._duration_ms = 0
        self._seeking = False

        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._audio_output.setVolume(0.5)
        self._player.setAudioOutput(self._audio_output)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.display_stack = QStackedWidget()
        self.display_stack.setObjectName("mediaDisplayStack")
        self.display_stack.setMinimumHeight(190)
        self.display_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.placeholder_label = QLabel("暂无预览")
        self.placeholder_label.setObjectName("mediaPreviewPlaceholder")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_widget = QVideoWidget()
        self.video_widget.setObjectName("mediaVideoWidget")
        self.video_widget.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self.video_widget.setMinimumHeight(190)
        self.display_stack.addWidget(self.placeholder_label)
        self.display_stack.addWidget(self.video_widget)
        self._player.setVideoOutput(self.video_widget)
        layout.addWidget(self.display_stack, 1)

        self.file_label = QLabel("未选择媒体")
        self.file_label.setObjectName("mediaPreviewFileLabel")
        self.file_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.file_label.setMinimumWidth(0)
        layout.addWidget(self.file_label)

        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(6)

        self.play_button = self._create_tool_button(_media_control_icon("play"), "播放")
        self.pause_button = self._create_tool_button(_media_control_icon("pause"), "暂停")
        self.stop_button = self._create_tool_button(_media_control_icon("stop"), "停止")
        self.play_button.clicked.connect(self.play)
        self.pause_button.clicked.connect(self.pause)
        self.stop_button.clicked.connect(self.stop)
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.pause_button)
        controls_layout.addWidget(self.stop_button)

        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setObjectName("mediaPositionSlider")
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderPressed.connect(self._on_slider_pressed)
        self.position_slider.sliderReleased.connect(self._on_slider_released)
        self.position_slider.sliderMoved.connect(self._on_slider_moved)
        controls_layout.addWidget(self.position_slider, 1)

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setObjectName("mediaTimeLabel")
        controls_layout.addWidget(self.time_label)
        layout.addLayout(controls_layout)

        self.status_label = QLabel("预览空闲")
        self.status_label.setObjectName("mediaPreviewStatusLabel")
        self.status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.status_label.setMinimumWidth(0)
        layout.addWidget(self.status_label)

        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.errorChanged.connect(self._on_error_changed)
        self._player.playbackStateChanged.connect(lambda _state: self._sync_control_state())
        self._sync_control_state()

    def set_media(
        self,
        path: Path | None,
        *,
        duration_seconds: float | None = None,
        label: str = "",
        has_video: bool | None = None,
    ) -> None:
        if path is None:
            self.clear()
            return
        if not path.exists():
            self.clear("预览文件不存在")
            return

        self._path = path
        self._fallback_duration_ms = _seconds_to_ms(duration_seconds)
        self._duration_ms = self._fallback_duration_ms
        self.file_label.setText(label or path.name)
        self.file_label.setToolTip(str(path))
        if has_video is False:
            self.status_label.setText("音频预览已载入")
            self.placeholder_label.setText("音频预览 · 无画面")
            self.display_stack.setCurrentWidget(self.placeholder_label)
        else:
            self.status_label.setText("预览已载入")
            self.display_stack.setCurrentWidget(self.video_widget)
        self._player.setSource(QUrl.fromLocalFile(str(path)))
        self._sync_duration_range()
        self._sync_time_label(self._player.position())
        self._sync_control_state()

    def clear(self, message: str = "暂无预览") -> None:
        self._player.stop()
        self._player.setSource(QUrl())
        self._path = None
        self._fallback_duration_ms = 0
        self._duration_ms = 0
        self.file_label.setText("未选择媒体")
        self.file_label.setToolTip("")
        self.status_label.setText(message)
        self.placeholder_label.setText(message)
        self.display_stack.setCurrentWidget(self.placeholder_label)
        self.position_slider.setRange(0, 0)
        self.position_slider.setValue(0)
        self._sync_time_label(0)
        self._sync_control_state()

    def play(self) -> None:
        if self._path is not None:
            self._player.play()

    def pause(self) -> None:
        self._player.pause()

    def stop(self) -> None:
        self._player.stop()
        self.position_slider.setValue(0)
        self._sync_time_label(0)

    def current_seconds(self) -> float:
        position = self._player.position()
        if position <= 0:
            position = self.position_slider.value()
        return max(0.0, position / 1000.0)

    def duration_seconds(self) -> float | None:
        if self._duration_ms <= 0:
            return None
        return self._duration_ms / 1000.0

    def _create_tool_button(self, icon: QIcon, tooltip: str) -> QToolButton:
        button = QToolButton()
        button.setObjectName("mediaToolButton")
        button.setIcon(icon)
        button.setIconSize(MEDIA_ICON_SIZE)
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        return button

    def _on_duration_changed(self, duration_ms: int) -> None:
        if duration_ms > 0:
            self._duration_ms = duration_ms
        elif self._fallback_duration_ms > 0:
            self._duration_ms = self._fallback_duration_ms
        else:
            self._duration_ms = 0
        self._sync_duration_range()
        self.duration_seconds_changed.emit(self._duration_ms / 1000.0 if self._duration_ms > 0 else 0.0)

    def _on_position_changed(self, position_ms: int) -> None:
        if not self._seeking:
            self.position_slider.setValue(max(0, position_ms))
        self._sync_time_label(position_ms)
        self.position_seconds_changed.emit(max(0.0, position_ms / 1000.0))

    def _on_error_changed(self) -> None:
        error_text = self._player.errorString()
        if error_text:
            self.status_label.setText(f"预览不可用：{error_text}")
        self._sync_control_state()

    def _on_slider_pressed(self) -> None:
        self._seeking = True

    def _on_slider_released(self) -> None:
        self._seeking = False
        position = self.position_slider.value()
        self._player.setPosition(position)
        self._sync_time_label(position)

    def _on_slider_moved(self, position_ms: int) -> None:
        self._sync_time_label(position_ms)
        self.position_seconds_changed.emit(max(0.0, position_ms / 1000.0))

    def _sync_duration_range(self) -> None:
        self.position_slider.setRange(0, max(0, self._duration_ms))

    def _sync_time_label(self, position_ms: int) -> None:
        self.time_label.setText(f"{_format_ms(position_ms)} / {_format_ms(self._duration_ms)}")

    def _sync_control_state(self) -> None:
        has_media = self._path is not None
        self.play_button.setEnabled(has_media)
        self.pause_button.setEnabled(has_media)
        self.stop_button.setEnabled(has_media)
        self.position_slider.setEnabled(has_media and self._duration_ms > 0)


def _seconds_to_ms(duration_seconds: float | None) -> int:
    if duration_seconds is None:
        return 0
    return max(0, int(round(duration_seconds * 1000)))


def _format_ms(value: int) -> str:
    total_seconds = max(0, int(round(value / 1000)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def _media_control_icon(shape: str) -> QIcon:
    icon = QIcon()
    icon.addPixmap(_draw_media_control_pixmap(shape, MEDIA_ICON_COLOR), QIcon.Mode.Normal)
    icon.addPixmap(_draw_media_control_pixmap(shape, MEDIA_ICON_COLOR), QIcon.Mode.Active)
    icon.addPixmap(_draw_media_control_pixmap(shape, MEDIA_ICON_DISABLED_COLOR), QIcon.Mode.Disabled)
    return icon


def _draw_media_control_pixmap(shape: str, color: QColor) -> QPixmap:
    pixmap = QPixmap(MEDIA_ICON_SIZE)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    if shape == "play":
        painter.drawPolygon(QPolygonF([QPointF(6, 4), QPointF(6, 14), QPointF(14, 9)]))
    elif shape == "pause":
        painter.drawRoundedRect(5, 4, 3, 10, 1, 1)
        painter.drawRoundedRect(10, 4, 3, 10, 1, 1)
    elif shape == "stop":
        painter.drawRoundedRect(5, 5, 8, 8, 1, 1)
    painter.end()
    return pixmap
