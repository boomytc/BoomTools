from __future__ import annotations

from dataclasses import dataclass

from desktop.app.controllers.main_controller import MainController
from desktop.app.services.config_service import ConfigService
from desktop.app.services.ffmpeg_service import FfmpegService
from desktop.app.services.log_service import LogService
from desktop.app.services.output_service import OutputService
from desktop.app.services.sleep_inhibitor import create_sleep_inhibitor
from desktop.app.tasks.task_manager import TaskManager
from desktop.app.ui.main_window import MainWindow
from desktop.app.ui.widgets.task_table_model import TaskTableModel


@dataclass
class AppBootstrap:
    window: MainWindow
    controller: MainController


def create_app() -> AppBootstrap:
    task_model = TaskTableModel()
    window = MainWindow(task_model)
    controller = MainController(
        window,
        task_model,
        config_service=ConfigService(),
        ffmpeg_service=FfmpegService(),
        output_service=OutputService(),
        log_service=LogService(),
        sleep_inhibitor=create_sleep_inhibitor(),
        task_manager=TaskManager(),
    )
    controller.initialize()
    return AppBootstrap(window=window, controller=controller)
