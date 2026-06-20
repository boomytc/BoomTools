from __future__ import annotations

import asyncio
import json
import re
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .config import FRONTEND_ROOT, ensure_data_dirs, get_config
from .ffmpeg import binary_available, ffmpeg_version, probe_media
from .jobs import JobManager, TERMINAL_STATUSES
from .schemas import AssetUploadResponse, HealthResponse, JobCreateRequest, JobCreateResponse, JobResponse, UploadResponse


app = FastAPI(title="BoomTools ffmpeg-web", version="0.1.0")
config = get_config()
job_manager = JobManager(config)


@app.on_event("startup")
async def startup() -> None:
    ensure_data_dirs()


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    version = await ffmpeg_version(config.ffmpeg_bin)
    return HealthResponse(
        ok=bool(version) and binary_available(config.ffprobe_bin),
        ffmpeg_available=bool(version),
        ffprobe_available=binary_available(config.ffprobe_bin),
        ffmpeg_path=config.ffmpeg_bin if binary_available(config.ffmpeg_bin) else None,
        ffmpeg_version=version,
    )


@app.post("/api/uploads", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)) -> UploadResponse:
    file_id = uuid.uuid4().hex
    original_name = file.filename or "input"
    ext = _safe_extension(original_name)
    upload_dir = config.uploads_root / file_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    input_path = upload_dir / f"input{ext}"

    size = 0
    with input_path.open("wb") as output:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            output.write(chunk)
    await file.close()

    media_info = await probe_media(config.ffprobe_bin, input_path)
    return UploadResponse(
        file_id=file_id,
        original_name=original_name,
        size=size,
        media_info=media_info,
    )


@app.post("/api/uploads/{file_id}/assets", response_model=AssetUploadResponse)
async def upload_asset(
    file_id: str,
    file: UploadFile = File(...),
    kind: str = Form("subtitle"),
) -> AssetUploadResponse:
    upload_dir = config.uploads_root / file_id
    if not _find_uploaded_input(upload_dir):
        raise HTTPException(status_code=404, detail="Uploaded file was not found")
    if kind != "subtitle":
        raise HTTPException(status_code=400, detail="Unsupported asset kind")

    original_name = file.filename or "subtitle"
    ext = _safe_subtitle_extension(original_name)
    asset_id = uuid.uuid4().hex
    asset_dir = upload_dir / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    asset_path = asset_dir / f"{asset_id}{ext}"

    size = 0
    with asset_path.open("wb") as output:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            output.write(chunk)
    await file.close()

    return AssetUploadResponse(
        asset_id=asset_id,
        kind=kind,
        original_name=original_name,
        size=size,
    )


@app.post("/api/jobs", response_model=JobCreateResponse)
async def create_job(payload: JobCreateRequest) -> JobCreateResponse:
    upload_dir = config.uploads_root / payload.file_id
    input_path = _find_uploaded_input(upload_dir)
    if not input_path:
        raise HTTPException(status_code=404, detail="Uploaded file was not found")
    job = job_manager.create_job(
        file_id=payload.file_id,
        operation=payload.operation,
        options=payload.options,
        input_path=input_path,
        upload_dir=upload_dir,
    )
    return JobCreateResponse(job_id=job.job_id, status=job.status)


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job was not found")
    return job.to_response()


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str) -> StreamingResponse:
    if not job_manager.get_job(job_id):
        raise HTTPException(status_code=404, detail="Job was not found")

    async def event_stream():
        queue = job_manager.subscribe(job_id)
        try:
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"event: update\ndata: {payload}\n\n"
                    status = json.loads(payload).get("status")
                    if status in TERMINAL_STATUSES:
                        break
                except asyncio.TimeoutError:
                    yield "event: ping\ndata: {}\n\n"
        finally:
            job_manager.unsubscribe(job_id, queue)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/jobs/{job_id}/download")
async def download_job(job_id: str) -> FileResponse:
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job was not found")
    if not job.output_path or not job.output_path.exists():
        raise HTTPException(status_code=404, detail="Output file was not found")
    return FileResponse(job.output_path, filename=job.output_name or job.output_path.name)


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str) -> dict[str, bool]:
    deleted = await job_manager.delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Job was not found")
    return {"deleted": True}


app.mount("/static", StaticFiles(directory=FRONTEND_ROOT / "static"), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(FRONTEND_ROOT / "index.html")


def _find_uploaded_input(upload_dir: Path) -> Path | None:
    if not upload_dir.exists():
        return None
    candidates = sorted(path for path in upload_dir.iterdir() if path.is_file() and path.name.startswith("input"))
    return candidates[0] if candidates else None


def _safe_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if not suffix:
        return ".bin"
    if not re.fullmatch(r"\.[a-z0-9]{1,8}", suffix):
        return ".bin"
    return suffix


def _safe_subtitle_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in {".srt", ".vtt", ".ass", ".ssa"}:
        raise HTTPException(status_code=400, detail="Subtitle file must be .srt, .vtt, .ass, or .ssa")
    return suffix
