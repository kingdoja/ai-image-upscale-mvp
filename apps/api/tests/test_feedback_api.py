from io import BytesIO

from fastapi import UploadFile

from app.jobs.service import create_job, process_job


def test_feedback_endpoint_accepts_valid_feedback(client, sample_image_bytes):
    create_response = client.post(
        "/api/upscale/jobs",
        data={"scale": "4", "mode": "both", "scene": "product"},
        files={"image": ("product.png", sample_image_bytes, "image/png")},
    )
    job_id = create_response.json()["job_id"]

    from app.database import SessionLocal
    from app.jobs.service import process_job

    db = SessionLocal()
    try:
        job = process_job(db, job_id)
        result_id = job.results[0].id
    finally:
        db.close()

    response = client.post(
        f"/api/upscale/jobs/{job_id}/feedback",
        json={
            "selected_result_id": result_id,
            "rating": 4,
            "usable": True,
            "issues": ["good"],
            "comment": "usable",
        },
    )

    assert response.status_code == 200
    assert response.json()["issues"] == ["good"]


def test_feedback_rejects_invalid_rating(client):
    response = client.post(
        "/api/upscale/jobs/up_missing/feedback",
        json={"selected_result_id": "res_missing", "rating": 6, "usable": False, "issues": [], "comment": ""},
    )

    assert response.status_code == 422


def test_feedback_rejects_invalid_issue_tag(client):
    response = client.post(
        "/api/upscale/jobs/up_missing/feedback",
        json={
            "selected_result_id": "res_missing",
            "rating": 3,
            "usable": False,
            "issues": ["bad_tag"],
            "comment": "",
        },
    )

    assert response.status_code == 422


def test_feedback_for_missing_job_returns_404(client):
    response = client.post(
        "/api/upscale/jobs/up_missing/feedback",
        json={"selected_result_id": "res_missing", "rating": 3, "usable": False, "issues": [], "comment": ""},
    )

    assert response.status_code == 404
