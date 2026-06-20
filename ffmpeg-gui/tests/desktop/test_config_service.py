from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from desktop.app.core.config import AppConfig
from desktop.app.runtime.binaries import binary_available
from desktop.app.services.config_service import ConfigService


def test_binary_available_accepts_file_path() -> None:
    with TemporaryDirectory() as tmp:
        binary = Path(tmp) / "ffmpeg"
        binary.write_text("#!/bin/sh\n", encoding="utf-8")
        assert binary_available(str(binary))


def test_config_service_roundtrip() -> None:
    with TemporaryDirectory() as tmp:
        config_path = Path(tmp) / "config.json"
        service = ConfigService(config_path)
        config = AppConfig(ffmpeg_bin="/opt/ffmpeg", ffprobe_bin="/opt/ffprobe", output_dir=Path(tmp) / "输出 目录")

        service.save(config)
        loaded = service.load()

    assert loaded.ffmpeg_bin == "/opt/ffmpeg"
    assert loaded.ffprobe_bin == "/opt/ffprobe"
    assert loaded.output_dir.name == "输出 目录"
