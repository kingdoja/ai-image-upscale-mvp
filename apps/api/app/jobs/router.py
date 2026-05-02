from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..config import get_settings
from ..schemas import FeedbackCreate, FeedbackRead, JobCreateResponse, JobListRead, JobRead
from .service import create_feedback, create_job, get_job, list_recent_jobs, process_job, serialize_job, serialize_job_summary


router = APIRouter(prefix="/api/upscale/jobs", tags=["upscale-jobs"])


@router.get("", response_model=JobListRead)
def list_upscale_jobs(db: Session = Depends(get_db)) -> dict:
    return {"jobs": [serialize_job_summary(job) for job in list_recent_jobs(db)]}


@router.post("", response_model=JobCreateResponse)
def create_upscale_job(
    image: UploadFile = File(...),
    scale: int = Form(...),
    mode: str = Form(...),
    scene: str = Form("product"),
    db: Session = Depends(get_db),
) -> JobCreateResponse:
    job = create_job(db, image=image, scale=scale, mode=mode, scene=scene)
    if get_settings().process_inline:
        job = process_job(db, job.id)
    return JobCreateResponse(job_id=job.id, status=job.status, estimated_seconds=90)


@router.get("/{job_id}", response_model=JobRead)
def read_upscale_job(job_id: str, db: Session = Depends(get_db)) -> dict:
    job = get_job(db, job_id)
    return serialize_job(job)


@router.post("/{job_id}/process", response_model=JobRead)
def process_upscale_job(job_id: str, db: Session = Depends(get_db)) -> dict:
    job = process_job(db, job_id)
    return serialize_job(job)


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
