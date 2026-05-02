from pathlib import Path
from io import BytesIO
import json
from typing import Iterable, List, Tuple
import zipfile

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import get_settings
from ..inference.base import ModelConfigurationError
from ..inference.diffusion import DiffusionUpscaleAdapter
from ..inference.realesrgan import RealESRGANAdapter
from ..inference.stub import StubUpscaleAdapter
from ..models import Feedback, Job, Result, new_id
from ..quality import evaluate_image
from ..schemas import ALLOWED_ISSUES, FeedbackCreate
from ..storage import create_thumbnail, result_path, save_upload, thumbnail_path


VALID_SCALES = {2, 4}
VALID_MODES = {"faithful", "realistic", "both"}
VALID_SCENES = {"product", "marketing", "ecommerce", "other"}


def _validate_job_options(scale: int, mode: str, scene: str) -> None:
    if scale not in VALID_SCALES:
        raise HTTPException(status_code=422, detail="scale must be 2 or 4")
    if mode not in VALID_MODES:
        raise HTTPException(status_code=422, detail="mode must be faithful, realistic, or both")
    if scene not in VALID_SCENES:
        raise HTTPException(status_code=422, detail="scene must be product, marketing, ecommerce, or other")


def create_job(
    db: Session,
    *,
    image: UploadFile,
    scale: int,
    mode: str,
    scene: str = "product",
    uploader_id: str = "internal-user",
) -> Job:
    _validate_job_options(scale, mode, scene)
    job_id = new_id("up")
    stored = save_upload(image, job_id)
    warnings = []
    if scene in {"marketing", "ecommerce"}:
        warnings.append("text_or_logo_review_recommended")
    job = Job(
        id=job_id,
        uploader_id=uploader_id,
        original_file_path=str(stored.path),
        original_hash=stored.sha256,
        scale=scale,
        mode=mode,
        scene=scene,
        status="queued",
    )
    job.warnings = warnings
    db.add(job)
    db.commit()
    db.refresh(job)
    enqueue_job(job.id)
    return job


def create_batch_jobs(
    db: Session,
    *,
    images: List[UploadFile],
    scale: int,
    mode: str,
    scene: str = "product",
    uploader_id: str = "internal-user",
) -> Tuple[str, List[Job]]:
    if not images:
        raise HTTPException(status_code=422, detail="at least one image is required")
    batch_id = new_id("batch")
    jobs = [
        create_job(
            db,
            image=image,
            scale=scale,
            mode=mode,
            scene=scene,
            uploader_id=uploader_id,
        )
        for image in images
    ]
    _write_batch_manifest(batch_id, [job.id for job in jobs])
    return batch_id, jobs


def _batch_manifest_path(batch_id: str) -> Path:
    return get_settings().storage_root / "batches" / f"{batch_id}.json"


def _write_batch_manifest(batch_id: str, job_ids: List[str]) -> None:
    path = _batch_manifest_path(batch_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"batch_id": batch_id, "job_ids": job_ids}, ensure_ascii=False), encoding="utf-8")


def get_batch_job_ids(batch_id: str) -> List[str]:
    path = _batch_manifest_path(batch_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Batch not found")
    payload = json.loads(path.read_text(encoding="utf-8"))
    job_ids = payload.get("job_ids", [])
    if not isinstance(job_ids, list):
        raise HTTPException(status_code=500, detail="Batch manifest is invalid")
    return [str(job_id) for job_id in job_ids]


def build_batch_results_zip(db: Session, batch_id: str) -> BytesIO:
    buffer = BytesIO()
    job_ids = get_batch_job_ids(batch_id)
    added = 0
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for job_id in job_ids:
            job = get_job(db, job_id)
            if job.status != "completed":
                continue
            for result in job.results:
                path = Path(result.file_path)
                if not path.exists():
                    continue
                archive.write(path, arcname=f"{job.id}-{result.result_type}{path.suffix}")
                added += 1
    if added == 0:
        raise HTTPException(status_code=404, detail="No completed results are available for this batch")
    buffer.seek(0)
    return buffer


def enqueue_job(job_id: str) -> None:
    settings = get_settings()
    if not settings.enqueue_jobs:
        return
    try:
        from redis import Redis
        from rq import Queue
    except ImportError as exc:
        raise RuntimeError("Redis/RQ dependencies are not installed") from exc
    queue = Queue("upscale", connection=Redis.from_url(settings.redis_url))
    queue.enqueue("app.workers.upscale_worker.process_job_by_id", job_id)


def get_job(db: Session, job_id: str) -> Job:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def list_recent_jobs(db: Session, limit: int = 20) -> List[Job]:
    return (
        db.query(Job)
        .order_by(Job.created_at.desc())
        .limit(limit)
        .all()
    )


def _public_path(path: str) -> str:
    p = Path(path)
    parts = p.parts
    if "storage" in parts:
        idx = parts.index("storage")
        return "/" + "/".join(parts[idx:])
    return path


def serialize_job(job: Job) -> dict:
    return {
        "job_id": job.id,
        "status": job.status,
        "scale": job.scale,
        "mode": job.mode,
        "original_url": _public_path(job.original_file_path),
        "warnings": job.warnings,
        "results": [
            {
                "id": result.id,
                "type": result.result_type,
                "url": _public_path(result.file_path),
                "thumbnail_url": _public_path(result.thumbnail_path),
                "model_name": result.model_name,
                "model_version": result.model_version,
                "quality_score": result.quality_score,
                "risk_level": result.risk_level,
            }
            for result in job.results
        ],
    }


def serialize_job_summary(job: Job) -> dict:
    risk_order = {"low": 0, "medium": 1, "high": 2}
    risk_level = "low"
    if job.results:
        risk_level = max((result.risk_level for result in job.results), key=lambda value: risk_order.get(value, 0))
    elif job.warnings:
        risk_level = "medium"
    thumbnail_url = _public_path(job.results[0].thumbnail_path) if job.results else None
    result_url = _public_path(job.results[0].file_path) if job.results else None
    return {
        "job_id": job.id,
        "status": job.status,
        "scale": job.scale,
        "mode": job.mode,
        "scene": job.scene,
        "warnings": job.warnings,
        "result_count": len(job.results),
        "thumbnail_url": thumbnail_url,
        "result_url": result_url,
        "risk_level": risk_level,
        "created_at": job.created_at,
    }


def _adapters_for_mode(mode: str) -> Iterable[Tuple[str, object]]:
    settings = get_settings()
    if mode in {"faithful", "both"}:
        if settings.faithful_backend == "realesrgan":
            yield "faithful", RealESRGANAdapter(
                executable_path=Path(settings.realesrgan_executable) if settings.realesrgan_executable else None,
                model_path=Path(settings.realesrgan_model_path) if settings.realesrgan_model_path else None,
                model=settings.realesrgan_model,
                timeout_seconds=settings.realesrgan_timeout_seconds,
            )
        else:
            yield "faithful", StubUpscaleAdapter(sharpen=True)
        yield "sharpened", StubUpscaleAdapter(sharpen=True)
    if mode in {"realistic", "both"}:
        if settings.realistic_backend == "stub":
            yield "realistic", StubUpscaleAdapter(sharpen=True)
        elif settings.realistic_backend != "disabled":
            yield "realistic", DiffusionUpscaleAdapter()


def process_job(db: Session, job_id: str) -> Job:
    job = get_job(db, job_id)
    job.status = "running"
    db.commit()

    try:
        created_results = 0
        input_path = Path(job.original_file_path)
        for result_type, adapter in _adapters_for_mode(job.mode):
            result_id = new_id("res")
            output_path = result_path(result_id)
            thumb_path = thumbnail_path(result_id)
            try:
                output = adapter.upscale(input_path, output_path, job.scale)
                create_thumbnail(output.output_path, thumb_path)
                quality = evaluate_image(
                    input_path,
                    output.output_path,
                    contains_text=job.scene in {"marketing", "ecommerce"},
                    contains_logo=job.scene in {"marketing", "ecommerce"},
                )
                result = Result(
                    id=result_id,
                    job_id=job.id,
                    result_type=result_type,
                    file_path=str(output.output_path),
                    thumbnail_path=str(thumb_path),
                    model_name=output.model_name,
                    model_version=output.model_version,
                    quality_score=quality.quality_score,
                    risk_level=quality.risk_level,
                )
                job.warnings = sorted(set(job.warnings + output.warnings + quality.warnings))
                db.add(result)
                created_results += 1
            except ModelConfigurationError as exc:
                job.warnings = sorted(set(job.warnings + [str(exc)]))
        if created_results == 0:
            raise RuntimeError("No result images were generated")
        job.status = "completed"
    except Exception as exc:
        job.status = "failed"
        job.warnings = sorted(set(job.warnings + [f"worker_failed: {exc}"]))
    db.commit()
    db.refresh(job)
    return job


def create_feedback(db: Session, job_id: str, payload: FeedbackCreate) -> Feedback:
    job = get_job(db, job_id)
    result = db.get(Result, payload.selected_result_id)
    if not result or result.job_id != job.id:
        raise HTTPException(status_code=404, detail="Selected result not found for this job")
    invalid = sorted(set(payload.issues) - ALLOWED_ISSUES)
    if invalid:
        raise HTTPException(status_code=422, detail=f"Invalid issue tags: {', '.join(invalid)}")
    feedback = Feedback(
        job_id=job.id,
        selected_result_id=result.id,
        rating=payload.rating,
        usable=payload.usable,
        comment=payload.comment,
    )
    feedback.issues = payload.issues
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback
