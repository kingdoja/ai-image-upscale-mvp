from . import __doc__ as _
from ..database import SessionLocal
from ..jobs.service import process_job


def process_job_by_id(job_id: str) -> str:
    db = SessionLocal()
    try:
        job = process_job(db, job_id)
        return job.status
    finally:
        db.close()
