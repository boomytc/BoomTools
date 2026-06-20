from __future__ import annotations

from pathlib import Path

from desktop.app.core.paths import OUTPUTS_DIR, ensure_runtime_dirs


class OutputService:
    def default_output_dir(self) -> Path:
        ensure_runtime_dirs()
        return OUTPUTS_DIR

    def normalize_output_dir(self, path: Path | None) -> Path:
        output_dir = path if path else self.default_output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
