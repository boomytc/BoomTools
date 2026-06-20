from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUTS_DIR = DATA_DIR / "outputs"
TEMP_DIR = DATA_DIR / "temp"
CACHE_DIR = DATA_DIR / "cache"
DEBUG_DIR = DATA_DIR / "debug"
LOGS_DIR = DATA_DIR / "logs"
RESOURCES_DIR = PROJECT_ROOT / "resources"
QSS_PATH = RESOURCES_DIR / "qss" / "app.qss"
CONFIG_PATH = DATA_DIR / "config.json"


def ensure_runtime_dirs() -> None:
    for path in (DATA_DIR, OUTPUTS_DIR, TEMP_DIR, CACHE_DIR, DEBUG_DIR, LOGS_DIR):
        path.mkdir(parents=True, exist_ok=True)
