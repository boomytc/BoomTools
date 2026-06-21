from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from desktop.app.core.config import AppConfig
from desktop.app.runtime.binaries import binary_available, runtime_health_snapshot
from desktop.app.services.config_service import ConfigService


def test_binary_available_accepts_file_path() -> None:
    with TemporaryDirectory() as tmp:
        binary = Path(tmp) / "ffmpeg"
        binary.write_text("#!/bin/sh\n", encoding="utf-8")
        binary.chmod(0o755)
        assert binary_available(str(binary))


def test_binary_available_rejects_plain_file_path() -> None:
    with TemporaryDirectory() as tmp:
        binary = Path(tmp) / "ffmpeg"
        binary.write_text("#!/bin/sh\n", encoding="utf-8")
        binary.chmod(0o644)
        assert not binary_available(str(binary))


def test_runtime_health_snapshot_requires_executable_paths() -> None:
    with TemporaryDirectory() as tmp:
        ffmpeg_bin = Path(tmp) / "ffmpeg"
        ffprobe_bin = Path(tmp) / "ffprobe"
        ffmpeg_bin.write_text("#!/bin/sh\n", encoding="utf-8")
        ffprobe_bin.write_text("#!/bin/sh\n", encoding="utf-8")
        ffmpeg_bin.chmod(0o755)
        ffprobe_bin.chmod(0o644)

        health = runtime_health_snapshot(str(ffmpeg_bin), str(ffprobe_bin))

    assert health.ffmpeg_available
    assert not health.ffprobe_available
    assert not health.ok


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
