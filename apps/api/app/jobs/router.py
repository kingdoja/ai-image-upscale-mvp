from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..config import get_settings
from ..schemas import BatchCreateResponse, FeedbackCreate, FeedbackRead, JobCreateResponse, JobListRead, JobRead, ModelStatusListRead
from .service import (
    create_batch_jobs,
    create_feedback,
    create_job,
    downloadable_result_path,
    first_downloadable_result_for_job,
    get_job,
    get_result,
    list_recent_jobs,
    process_job,
    build_batch_results_zip,
    build_model_statuses,
    build_batch_evaluation_report,
    build_batch_risk_samples,
    render_evaluation_report_csv,
    render_evaluation_report_markdown,
    render_risk_samples_csv,
    render_risk_samples_markdown,
    serialize_job,
    serialize_job_summary,
)


router = APIRouter(prefix="/api/upscale/jobs", tags=["upscale-jobs"])
batches_router = APIRouter(prefix="/api/upscale/batches", tags=["upscale-batches"])
reports_router = APIRouter(prefix="/api/upscale/reports", tags=["upscale-reports"])
models_router = APIRouter(prefix="/api/upscale/models", tags=["upscale-models"])
results_router = APIRouter(prefix="/api/upscale/results", tags=["upscale-results"])


@router.get("", response_model=JobListRead)
def list_upscale_jobs(db: Session = Depends(get_db)) -> dict:
    return {"jobs": [serialize_job_summary(job) for job in list_recent_jobs(db)]}


@router.post("", response_model=JobCreateResponse)
def create_upscale_job(
    image: UploadFile = File(...),
    scale: int = Form(...),
    mode: str = Form(...),
    scene: str = Form("product"),
    candidates: List[str] = Form(default=None),
    db: Session = Depends(get_db),
) -> JobCreateResponse:
    job = create_job(db, image=image, scale=scale, mode=mode, scene=scene, selected_candidates=candidates)
    if get_settings().process_inline:
        job = process_job(db, job.id)
    return JobCreateResponse(job_id=job.id, status=job.status, estimated_seconds=90)


@batches_router.post("", response_model=BatchCreateResponse)
def create_upscale_batch(
    images: List[UploadFile] = File(...),
    scale: int = Form(...),
    mode: str = Form(...),
    scene: str = Form("product"),
    candidates: List[str] = Form(default=None),
    db: Session = Depends(get_db),
) -> BatchCreateResponse:
    batch_id, jobs = create_batch_jobs(db, images=images, scale=scale, mode=mode, scene=scene, selected_candidates=candidates)
    if get_settings().process_inline:
        jobs = [process_job(db, job.id) for job in jobs]
    return BatchCreateResponse(
        batch_id=batch_id,
        job_ids=[job.id for job in jobs],
        created_count=len(jobs),
    )


@batches_router.get("/{batch_id}/download")
def download_upscale_batch(batch_id: str, db: Session = Depends(get_db)) -> StreamingResponse:
    archive = build_batch_results_zip(db, batch_id)
    return StreamingResponse(
        archive,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{batch_id}-results.zip"'},
    )


@reports_router.get("/{batch_id}")
def download_upscale_report(batch_id: str, format: str = "markdown", db: Session = Depends(get_db)) -> Response:
    report = build_batch_evaluation_report(db, batch_id)
    if format == "csv":
        return Response(
            content=render_evaluation_report_csv(report),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{batch_id}-evaluation.csv"'},
        )
    if format in {"markdown", "md"}:
        return Response(
            content=render_evaluation_report_markdown(report),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{batch_id}-evaluation.md"'},
        )
    raise HTTPException(status_code=422, detail="format must be markdown or csv")


@reports_router.get("/{batch_id}/risk-samples")
def download_risk_samples(batch_id: str, format: str = "markdown", db: Session = Depends(get_db)) -> Response:
    report = build_batch_risk_samples(db, batch_id)
    if format == "csv":
        return Response(
            content=render_risk_samples_csv(report),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{batch_id}-risk-samples.csv"'},
        )
    if format in {"markdown", "md"}:
        return Response(
            content=render_risk_samples_markdown(report),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{batch_id}-risk-samples.md"'},
        )
    raise HTTPException(status_code=422, detail="format must be markdown or csv")


@models_router.get("/status", response_model=ModelStatusListRead)
def read_model_statuses() -> dict:
    return build_model_statuses()


@router.get("/{job_id}", response_model=JobRead)
def read_upscale_job(job_id: str, db: Session = Depends(get_db)) -> dict:
    job = get_job(db, job_id)
    return serialize_job(job)


@router.post("/{job_id}/process", response_model=JobRead)
def process_upscale_job(job_id: str, db: Session = Depends(get_db)) -> dict:
    job = process_job(db, job_id)
    return serialize_job(job)


@router.get("/{job_id}/download")
def download_job_result(job_id: str, db: Session = Depends(get_db)) -> FileResponse:
    job = get_job(db, job_id)
    result = first_downloadable_result_for_job(job)
    path = downloadable_result_path(result)
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=f"{result.id}{path.suffix}",
    )


@results_router.get("/{result_id}/download")
def download_result(result_id: str, db: Session = Depends(get_db)) -> FileResponse:
    result = get_result(db, result_id)
    path = downloadable_result_path(result)
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=f"{result.id}{path.suffix}",
    )


@router.post("/{job_id}/feedback", response_model=FeedbackRead)
def create_job_feedback(job_id: str, payload: FeedbackCreate, db: Session = Depends(get_db)) -> FeedbackRead:
    feedback = create_feedback(db, job_id, payload)
    return FeedbackRead(
        id=feedback.id,
        job_id=feedback.job_id,
        selected_result_id=feedback.selected_result_id,
        rating=feedback.rating,
        usable=feedback.usable,
        issues=feedback.issues,
        comment=feedback.comment,
        created_at=feedback.created_at,
    )
