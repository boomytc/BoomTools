from __future__ import annotations

import zipfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from desktop.app.core.paths import OUTPUTS_DIR, ensure_runtime_dirs
from shared.contracts import TaskRecord, TaskStatus


class ZipCancelledError(RuntimeError):
    """Raised when a batch ZIP request is cancelled between file chunks."""


@dataclass(frozen=True)
class BatchZipResult:
    archive_path: Path | None
    packed_count: int
    skipped_count: int


class OutputService:
    def default_output_dir(self) -> Path:
        ensure_runtime_dirs()
        return OUTPUTS_DIR

    def normalize_output_dir(self, path: Path | None) -> Path:
        output_dir = path if path else self.default_output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def zip_successful_outputs(
        self,
        records: Iterable[TaskRecord],
        output_dir: Path | None,
        *,
        timestamp: datetime | None = None,
        cancel_requested: Callable[[], bool] | None = None,
    ) -> BatchZipResult:
        selected_paths: list[Path] = []
        skipped_count = 0
        for record in records:
            output_path = record.output_path
            if record.status is not TaskStatus.succeeded or output_path is None:
                skipped_count += 1
                continue
            if not _is_existing_file(output_path):
                skipped_count += 1
                continue
            selected_paths.append(output_path)

        if not selected_paths:
            return BatchZipResult(archive_path=None, packed_count=0, skipped_count=skipped_count)

        target_dir = self.normalize_output_dir(output_dir)
        archive_path = _unique_output_path(target_dir / f"ffmpeg-gui-batch-{_timestamp_label(timestamp)}.zip")
        used_names: set[str] = set()
        try:
            with zipfile.ZipFile(archive_path, "w", allowZip64=True) as archive:
                for output_path in selected_paths:
                    _raise_if_cancelled(cancel_requested)
                    arcname = _unique_archive_name(output_path.name, used_names)
                    _write_file_to_zip(archive, output_path, arcname, cancel_requested)
        except ZipCancelledError:
            archive_path.unlink(missing_ok=True)
            raise
        except Exception:
            archive_path.unlink(missing_ok=True)
            raise

        return BatchZipResult(
            archive_path=archive_path,
            packed_count=len(selected_paths),
            skipped_count=skipped_count,
        )


def _is_existing_file(path: Path) -> bool:
    try:
        return path.is_file()
    except OSError:
        return False


def _timestamp_label(timestamp: datetime | None) -> str:
    return (timestamp or datetime.now()).strftime("%Y%m%d-%H%M%S")


def _unique_output_path(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(2, 10_000):
        candidate = path.with_name(f"{path.stem}-{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise OSError(f"无法生成唯一输出文件名：{path}")


def _unique_archive_name(filename: str, used_names: set[str]) -> str:
    path = Path(filename)
    stem = path.stem or "output"
    suffix = path.suffix
    candidate = filename or "output"
    if candidate not in used_names:
        used_names.add(candidate)
        return candidate
    for index in range(2, 10_000):
        candidate = f"{stem}-{index}{suffix}"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
    raise ValueError(f"无法生成唯一 ZIP 内文件名：{filename}")


def _write_file_to_zip(
    archive: zipfile.ZipFile,
    source_path: Path,
    arcname: str,
    cancel_requested: Callable[[], bool] | None,
) -> None:
    info = zipfile.ZipInfo.from_file(source_path, arcname)
    info.compress_type = zipfile.ZIP_DEFLATED
    with source_path.open("rb") as source, archive.open(info, "w") as target:
        while True:
            _raise_if_cancelled(cancel_requested)
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            target.write(chunk)


def _raise_if_cancelled(cancel_requested: Callable[[], bool] | None) -> None:
    if cancel_requested is not None and cancel_requested():
        raise ZipCancelledError("打包已取消")
