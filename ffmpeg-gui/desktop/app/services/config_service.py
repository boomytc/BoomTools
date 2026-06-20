from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from desktop.app.core.config import AppConfig
from desktop.app.core.paths import CONFIG_PATH, ensure_runtime_dirs


class ConfigService:
    def __init__(self, config_path: Path = CONFIG_PATH) -> None:
        self.config_path = config_path

    def load(self) -> AppConfig:
        defaults = AppConfig.defaults()
        if not self.config_path.exists():
            return defaults
        try:
            raw = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return defaults
        return AppConfig(
            ffmpeg_bin=str(raw.get("ffmpeg_bin") or defaults.ffmpeg_bin),
            ffprobe_bin=str(raw.get("ffprobe_bin") or defaults.ffprobe_bin),
            output_dir=Path(raw.get("output_dir") or defaults.output_dir),
        )

    def save(self, config: AppConfig) -> None:
        ensure_runtime_dirs()
        payload: dict[str, Any] = asdict(config)
        payload["output_dir"] = str(config.output_dir)
        self.config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
