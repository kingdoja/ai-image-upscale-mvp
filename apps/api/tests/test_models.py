from app.models import Feedback, Job, Result


def test_job_result_feedback_relationships(db_session):
    job = Job(
        id="up_test",
        uploader_id="u1",
        original_file_path="/tmp/original.png",
        original_hash="abc",
        scale=4,
        mode="both",
        scene="product",
        status="queued",
    )
    job.warnings = ["text_or_logo_review_recommended"]
    result = Result(
        id="res_test",
        job_id="up_test",
        result_type="faithful",
        file_path="/tmp/result.png",
        thumbnail_path="/tmp/result.thumb.jpg",
        model_name="stub",
        model_version="0.1",
        quality_score=0.8,
        risk_level="low",
    )
    feedback = Feedback(
        id="fb_test",
        job_id="up_test",
        selected_result_id="res_test",
        rating=4,
        usable=True,
        comment="usable",
    )
    feedback.issues = ["good"]

    db_session.add(job)
    db_session.add(result)
    db_session.add(feedback)
    db_session.commit()

    loaded = db_session.get(Job, "up_test")
    assert loaded.warnings == ["text_or_logo_review_recommended"]
    assert loaded.results[0].result_type == "faithful"
    assert loaded.feedback[0].issues == ["good"]
