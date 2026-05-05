from io import BytesIO
from pathlib import Path
import zipfile

from PIL import Image, ImageDraw


def test_download_batch_evaluation_report_as_markdown(client, sample_image_bytes):
    created = client.post(
        "/api/upscale/batches",
        data={"scale": "4", "mode": "faithful", "scene": "ecommerce"},
        files=[
            ("images", ("first.png", sample_image_bytes, "image/png")),
            ("images", ("second.png", sample_image_bytes, "image/png")),
        ],
    ).json()
    processed = client.post(f"/api/upscale/jobs/{created['job_ids'][0]}/process").json()
    result_id = processed["results"][0]["id"]
    client.post(
        f"/api/upscale/jobs/{created['job_ids'][0]}/feedback",
        json={
            "selected_result_id": result_id,
            "rating": 4,
            "usable": True,
            "issues": ["good", "logo_error"],
            "comment": "[evaluation]\nclarity=5\nstructure=4\nnotes=Logo needs review",
        },
    )

    from app.database import SessionLocal
    from app.models import Job, Result

    with SessionLocal() as session:
        result = session.get(Result, result_id)
        result.risk_level = "high"
        failed_job = session.get(Job, created["job_ids"][1])
        failed_job.status = "failed"
        session.commit()

    response = client.get(f"/api/upscale/reports/{created['batch_id']}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "样本数: 2" in response.text
    assert "完成数: 1" in response.text
    assert "失败数: 1" in response.text
    assert "平均评分: 4.0" in response.text
    assert "logo_error: 1" in response.text
    assert created["job_ids"][0] in response.text


def test_download_batch_evaluation_report_as_csv(client, sample_image_bytes):
    created = client.post(
        "/api/upscale/batches",
        data={"scale": "4", "mode": "faithful", "scene": "product"},
        files=[("images", ("first.png", sample_image_bytes, "image/png"))],
    ).json()
    processed = client.post(f"/api/upscale/jobs/{created['job_ids'][0]}/process").json()
    result_id = processed["results"][0]["id"]
    client.post(
        f"/api/upscale/jobs/{created['job_ids'][0]}/feedback",
        json={
            "selected_result_id": result_id,
            "rating": 5,
            "usable": True,
            "issues": ["good"],
            "comment": "[evaluation]\nclarity=5\nnotes=usable",
        },
    )

    response = client.get(f"/api/upscale/reports/{created['batch_id']}?format=csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "job_id,status,scale,mode,scene,risk_level,rating,usable,issues" in response.text
    assert f"{created['job_ids'][0]},completed,4,faithful,product,low,5,True,good" in response.text


def test_download_batch_evaluation_report_csv_includes_semantic_risk_reasons(client, sample_image_bytes):
    created = client.post(
        "/api/upscale/batches",
        data={"scale": "4", "mode": "realistic", "scene": "marketing"},
        files=[("images", ("poster.png", sample_image_bytes, "image/png"))],
    ).json()
    client.post(f"/api/upscale/jobs/{created['job_ids'][0]}/process")

    response = client.get(f"/api/upscale/reports/{created['batch_id']}?format=csv")

    assert response.status_code == 200
    assert "semantic_risks,protected_regions,routing_reasons" in response.text
    assert "text_region_requires_review;logo_region_requires_review" in response.text
    assert "text:0,6,16,4" in response.text
    assert "logo:0,0,4,2" in response.text
    assert "protected_risk_regions" in response.text


def test_batch_evaluation_report_reads_persisted_semantic_manifest(client, sample_image_bytes):
    created = client.post(
        "/api/upscale/batches",
        data={"scale": "4", "mode": "realistic", "scene": "marketing"},
        files=[("images", ("poster.png", sample_image_bytes, "image/png"))],
    ).json()
    client.post(f"/api/upscale/jobs/{created['job_ids'][0]}/process")

    from app.database import SessionLocal
    from app.models import Job

    with SessionLocal() as session:
        job = session.get(Job, created["job_ids"][0])
        original_path = Path(job.original_file_path)
    image = Image.new("RGB", (800, 600), color=(245, 245, 245))
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 36, 180, 92), fill=(10, 10, 10))
    draw.rectangle((120, 430, 700, 478), fill=(20, 20, 20))
    image.save(original_path)

    response = client.get(f"/api/upscale/reports/{created['batch_id']}?format=csv")

    assert response.status_code == 200
    assert "text:0,6,16,4" in response.text
    assert "logo:0,0,4,2" in response.text
    assert "text:120,430,581,49" not in response.text


def test_download_batch_risk_samples_csv_for_training_dataset(client, sample_image_bytes):
    created = client.post(
        "/api/upscale/batches",
        data={"scale": "4", "mode": "faithful", "scene": "ecommerce"},
        files=[
            ("images", ("logo.png", sample_image_bytes, "image/png")),
            ("images", ("structure.png", sample_image_bytes, "image/png")),
            ("images", ("failed.png", sample_image_bytes, "image/png")),
        ],
    ).json()
    first = client.post(f"/api/upscale/jobs/{created['job_ids'][0]}/process").json()
    second = client.post(f"/api/upscale/jobs/{created['job_ids'][1]}/process").json()
    client.post(
        f"/api/upscale/jobs/{created['job_ids'][0]}/feedback",
        json={
            "selected_result_id": first["results"][0]["id"],
            "rating": 2,
            "usable": False,
            "issues": ["logo_error", "color_shift"],
            "comment": "Logo and color need review",
        },
    )
    client.post(
        f"/api/upscale/jobs/{created['job_ids'][1]}/feedback",
        json={
            "selected_result_id": second["results"][0]["id"],
            "rating": 3,
            "usable": False,
            "issues": ["structure_changed", "fake_texture"],
            "comment": "Structure changed",
        },
    )

    from app.database import SessionLocal
    from app.models import Job, Result

    with SessionLocal() as session:
        result = session.get(Result, first["results"][0]["id"])
        result.risk_level = "high"
        failed_job = session.get(Job, created["job_ids"][2])
        failed_job.status = "failed"
        failed_job.warnings = ["worker_failed: test"]
        session.commit()

    response = client.get(f"/api/upscale/reports/{created['batch_id']}/risk-samples?format=csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "job_id,original_path,result_path,scale,mode,scene,status,risk_level,rating,usable,issues,suggested_action" in response.text
    assert "logo_error;color_shift" in response.text
    assert "structure_changed;fake_texture" in response.text
    assert "人工回贴 Logo/文字并进入负样本复盘" in response.text
    assert "重新处理或检查推理服务配置" in response.text
    assert "仅供本地训练/评估使用，不上传第三方公共服务" in response.text


def test_download_batch_risk_samples_markdown_lists_review_scope(client, sample_image_bytes):
    created = client.post(
        "/api/upscale/batches",
        data={"scale": "4", "mode": "faithful", "scene": "marketing"},
        files=[("images", ("logo.png", sample_image_bytes, "image/png"))],
    ).json()
    processed = client.post(f"/api/upscale/jobs/{created['job_ids'][0]}/process").json()
    client.post(
        f"/api/upscale/jobs/{created['job_ids'][0]}/feedback",
        json={
            "selected_result_id": processed["results"][0]["id"],
            "rating": 2,
            "usable": False,
            "issues": ["logo_error"],
            "comment": "Logo mismatch",
        },
    )

    response = client.get(f"/api/upscale/reports/{created['batch_id']}/risk-samples")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "失败/高风险样本清单" in response.text
    assert "仅供本地训练/评估使用，不上传第三方公共服务" in response.text
    assert "Logo/文字错误" in response.text
    assert created["job_ids"][0] in response.text


def test_create_job_accepts_valid_upload(client, sample_image_bytes):
    response = client.post(
        "/api/upscale/jobs",
        data={"scale": "4", "mode": "both", "scene": "product"},
        files={"image": ("product.png", sample_image_bytes, "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["job_id"].startswith("up_")


def test_create_job_persists_selected_candidates_and_processes_only_selected(client, sample_image_bytes):
    created = client.post(
        "/api/upscale/jobs",
        data={"scale": "4", "mode": "both", "scene": "product", "candidates": ["hat", "faithful"]},
        files={"image": ("product.png", sample_image_bytes, "image/png")},
    ).json()

    processed = client.post(f"/api/upscale/jobs/{created['job_id']}/process").json()

    assert processed["upscale_plan"]["candidate_types"] == ["faithful", "hat"]
    assert [result["type"] for result in processed["results"]] == ["faithful"]
    assert processed["routing_decision"]["skipped_candidate_types"] == ["hat"]


def test_create_job_rejects_removed_or_invalid_selected_candidate(client, sample_image_bytes):
    response = client.post(
        "/api/upscale/jobs",
        data={"scale": "4", "mode": "both", "scene": "product", "candidates": ["material_guard"]},
        files={"image": ("product.png", sample_image_bytes, "image/png")},
    )

    assert response.status_code == 422

    removed = client.post(
        "/api/upscale/jobs",
        data={"scale": "4", "mode": "both", "scene": "product", "candidates": ["sharpened"]},
        files={"image": ("product.png", sample_image_bytes, "image/png")},
    )

    assert removed.status_code == 422


def test_create_job_can_process_inline_for_local_demo(client, sample_image_bytes, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("UPSCALE_PROCESS_INLINE", "true")
    get_settings.cache_clear()

    response = client.post(
        "/api/upscale/jobs",
        data={"scale": "4", "mode": "faithful", "scene": "product"},
        files={"image": ("product.png", sample_image_bytes, "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"

    detail = client.get(f"/api/upscale/jobs/{payload['job_id']}")
    assert detail.status_code == 200
    assert detail.json()["results"][0]["type"] == "faithful"
    get_settings.cache_clear()


def test_list_jobs_returns_recent_jobs(client, sample_image_bytes):
    first = client.post(
        "/api/upscale/jobs",
        data={"scale": "4", "mode": "faithful", "scene": "product"},
        files={"image": ("first.png", sample_image_bytes, "image/png")},
    ).json()
    second = client.post(
        "/api/upscale/jobs",
        data={"scale": "2", "mode": "both", "scene": "marketing"},
        files={"image": ("second.png", sample_image_bytes, "image/png")},
    ).json()

    response = client.get("/api/upscale/jobs")

    assert response.status_code == 200
    payload = response.json()
    assert [job["job_id"] for job in payload["jobs"]] == [second["job_id"], first["job_id"]]
    assert payload["jobs"][0]["status"] == "queued"
    assert payload["jobs"][0]["scale"] == 2
    assert payload["jobs"][0]["mode"] == "both"
    assert payload["jobs"][0]["scene"] == "marketing"


def test_create_batch_creates_independent_jobs(client, sample_image_bytes):
    response = client.post(
        "/api/upscale/batches",
        data={"scale": "4", "mode": "faithful", "scene": "product"},
        files=[
            ("images", ("first.png", sample_image_bytes, "image/png")),
            ("images", ("second.png", sample_image_bytes, "image/png")),
        ],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["batch_id"].startswith("batch_")
    assert payload["created_count"] == 2
    assert len(payload["job_ids"]) == 2
    assert payload["job_ids"][0] != payload["job_ids"][1]

    jobs = client.get("/api/upscale/jobs").json()["jobs"]
    assert [job["job_id"] for job in jobs] == list(reversed(payload["job_ids"]))


def test_download_batch_returns_zip_with_completed_results(client, sample_image_bytes):
    created = client.post(
        "/api/upscale/batches",
        data={"scale": "4", "mode": "faithful", "scene": "product"},
        files=[
            ("images", ("first.png", sample_image_bytes, "image/png")),
            ("images", ("second.png", sample_image_bytes, "image/png")),
        ],
    ).json()
    for job_id in created["job_ids"]:
        client.post(f"/api/upscale/jobs/{job_id}/process")

    response = client.get(f"/api/upscale/batches/{created['batch_id']}/download")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(BytesIO(response.content)) as archive:
        names = archive.namelist()
    assert len(names) == 2
    assert all(name.endswith(".png") for name in names)
    assert all(name.startswith("up_") for name in names)


def test_list_jobs_includes_thumbnail_and_risk_summary(client, sample_image_bytes):
    created = client.post(
        "/api/upscale/jobs",
        data={"scale": "4", "mode": "faithful", "scene": "ecommerce"},
        files={"image": ("detail.png", sample_image_bytes, "image/png")},
    ).json()
    client.post(f"/api/upscale/jobs/{created['job_id']}/process")

    response = client.get("/api/upscale/jobs")

    assert response.status_code == 200
    job = response.json()["jobs"][0]
    assert job["job_id"] == created["job_id"]
    assert job["thumbnail_url"].startswith("/storage/thumbnails/")
    assert job["result_url"].startswith("/storage/results/")
    assert job["risk_level"] == "medium"


def test_process_job_endpoint_completes_queued_job(client, sample_image_bytes):
    created = client.post(
        "/api/upscale/jobs",
        data={"scale": "4", "mode": "faithful", "scene": "product"},
        files={"image": ("product.png", sample_image_bytes, "image/png")},
    ).json()

    response = client.post(f"/api/upscale/jobs/{created['job_id']}/process")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["results"][0]["type"] == "faithful"


def test_download_result_endpoint_returns_attachment(client, sample_image_bytes):
    created = client.post(
        "/api/upscale/jobs",
        data={"scale": "4", "mode": "faithful", "scene": "product"},
        files={"image": ("product.png", sample_image_bytes, "image/png")},
    ).json()
    processed = client.post(f"/api/upscale/jobs/{created['job_id']}/process").json()
    result_id = processed["results"][0]["id"]

    with client.stream("GET", f"/api/upscale/results/{result_id}/download") as response:
        content = response.read()

    assert response.status_code == 200
    assert response.headers["content-disposition"].startswith("attachment;")
    assert result_id in response.headers["content-disposition"]
    assert content


def test_download_job_result_endpoint_returns_first_ordered_result(client, sample_image_bytes):
    created = client.post(
        "/api/upscale/jobs",
        data={"scale": "4", "mode": "faithful", "scene": "product"},
        files={"image": ("product.png", sample_image_bytes, "image/png")},
    ).json()
    processed = client.post(f"/api/upscale/jobs/{created['job_id']}/process").json()

    with client.stream("GET", f"/api/upscale/jobs/{created['job_id']}/download") as response:
        content = response.read()

    assert response.status_code == 200
    assert response.headers["content-disposition"].startswith("attachment;")
    assert processed["results"][0]["id"] in response.headers["content-disposition"]
    assert content


def test_job_detail_includes_original_url_and_result_model_metadata(client, sample_image_bytes):
    created = client.post(
        "/api/upscale/jobs",
        data={"scale": "4", "mode": "faithful", "scene": "product"},
        files={"image": ("product.png", sample_image_bytes, "image/png")},
    ).json()
    client.post(f"/api/upscale/jobs/{created['job_id']}/process")

    response = client.get(f"/api/upscale/jobs/{created['job_id']}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["original_url"].startswith("/storage/originals/")
    assert payload["results"][0]["model_name"]
    assert payload["results"][0]["model_version"]
    assert payload["understanding"]["scene"] == "product"
    assert payload["understanding"]["controller_version"] == "semantic-controller-v0.10.0"
    assert payload["understanding"]["data_usage_policy"] == "inference_only"
    assert "low_resolution_input" in payload["understanding"]["degradation_types"]
    assert payload["upscale_plan"]["candidate_types"][0] == "faithful"
    assert payload["upscale_plan"]["policy_version"] == "routing-policy-v0.10.0"
    assert payload["routing_decision"]["candidate_types"][0] == "faithful"
    assert payload["routing_decision"]["policy_version"] == "routing-policy-v0.10.0"
    assert payload["data_governance"]["training_state"] == "not_approved_for_training"


def test_marketing_job_detail_exposes_semantic_review_plan(client, sample_image_bytes):
    created = client.post(
        "/api/upscale/jobs",
        data={"scale": "4", "mode": "realistic", "scene": "marketing"},
        files={"image": ("poster.png", sample_image_bytes, "image/png")},
    ).json()
    client.post(f"/api/upscale/jobs/{created['job_id']}/process")

    payload = client.get(f"/api/upscale/jobs/{created['job_id']}").json()

    assert payload["understanding"]["review_required"] is True
    assert "text_region_requires_review" in payload["understanding"]["detected_risks"]
    assert payload["upscale_plan"]["candidate_types"][0] == "faithful"
    assert "realistic" in payload["upscale_plan"]["candidate_types"]
    assert payload["upscale_plan"]["protected_region_details"][0]["type"] == "text"
    assert payload["upscale_plan"]["protected_region_details"][0]["bbox"] == [0, 6, 16, 4]
    assert payload["upscale_plan"]["protected_region_details"][0]["source"] == "layout_heuristic"
    assert "protected_risk_regions" in payload["routing_decision"]["reasons"]
    assert payload["routing_decision"]["executed_candidate_types"] == ["faithful"]
    assert payload["routing_decision"]["skipped_candidate_types"] == ["realistic"]
    assert payload["routing_decision"]["skip_reasons"]["realistic"] == "backend_disabled_or_not_configured"


def test_job_detail_reads_persisted_semantic_manifest_after_original_changes(client, sample_image_bytes):
    created = client.post(
        "/api/upscale/jobs",
        data={"scale": "4", "mode": "realistic", "scene": "marketing"},
        files={"image": ("poster.png", sample_image_bytes, "image/png")},
    ).json()
    client.post(f"/api/upscale/jobs/{created['job_id']}/process")

    from app.database import SessionLocal
    from app.models import Job

    with SessionLocal() as session:
        job = session.get(Job, created["job_id"])
        original_path = Path(job.original_file_path)
    manifest_path = original_path.parents[3] / "manifests" / f"{created['job_id']}.json"
    assert manifest_path.exists()

    image = Image.new("RGB", (800, 600), color=(245, 245, 245))
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 36, 180, 92), fill=(10, 10, 10))
    draw.rectangle((120, 430, 700, 478), fill=(20, 20, 20))
    image.save(original_path)

    payload = client.get(f"/api/upscale/jobs/{created['job_id']}").json()

    assert payload["upscale_plan"]["protected_region_details"][0]["bbox"] == [0, 6, 16, 4]
    assert payload["upscale_plan"]["protected_region_details"][0]["source"] == "layout_heuristic"
    assert payload["upscale_plan"]["protected_region_details"][1]["bbox"] == [0, 0, 4, 2]


def test_create_job_rejects_invalid_scale(client, sample_image_bytes):
    response = client.post(
        "/api/upscale/jobs",
        data={"scale": "8", "mode": "both", "scene": "product"},
        files={"image": ("product.png", sample_image_bytes, "image/png")},
    )

    assert response.status_code == 422


def test_create_job_rejects_invalid_mode(client, sample_image_bytes):
    response = client.post(
        "/api/upscale/jobs",
        data={"scale": "4", "mode": "magic", "scene": "product"},
        files={"image": ("product.png", sample_image_bytes, "image/png")},
    )

    assert response.status_code == 422


def test_create_job_requires_file(client):
    response = client.post("/api/upscale/jobs", data={"scale": "4", "mode": "both", "scene": "product"})

    assert response.status_code == 422


def test_get_unknown_job_returns_404(client):
    response = client.get("/api/upscale/jobs/up_missing")

    assert response.status_code == 404


def test_model_status_reports_default_demo_and_disabled_models(client):
    response = client.get("/api/upscale/models/status")

    assert response.status_code == 200
    payload = response.json()
    assert [model["id"] for model in payload["models"]] == ["faithful", "swinir", "hat"]
    assert payload["models"][0]["label"] == "Real-ESRGAN"
    assert payload["models"][0]["status"] == "demo"
    assert payload["models"][0]["configured"] is True
    assert payload["models"][0]["backend"] == "stub"
    assert payload["models"][1]["status"] == "disabled"
    assert payload["models"][2]["status"] == "disabled"


def test_model_status_reports_external_models_ready(client, tmp_path, monkeypatch):
    from app.config import get_settings

    executable = tmp_path / "realesrgan.exe"
    executable.write_text("fake executable", encoding="utf-8")
    realesrgan_models = tmp_path / "realesrgan-models"
    realesrgan_models.mkdir()
    (realesrgan_models / "realesrgan-x4plus.param").write_text("fake param", encoding="utf-8")
    swinir_repo = tmp_path / "swinir-repo"
    swinir_repo.mkdir()
    swinir_model = tmp_path / "swinir.pth"
    swinir_model.write_text("fake weights", encoding="utf-8")
    hat_repo = tmp_path / "hat-repo"
    hat_repo.mkdir()
    hat_model = tmp_path / "hat.pth"
    hat_model.write_text("fake weights", encoding="utf-8")

    monkeypatch.setenv("UPSCALE_FAITHFUL_BACKEND", "realesrgan")
    monkeypatch.setenv("REALESRGAN_EXECUTABLE", str(executable))
    monkeypatch.setenv("REALESRGAN_MODEL_PATH", str(realesrgan_models))
    monkeypatch.setenv("UPSCALE_SWINIR_BACKEND", "external")
    monkeypatch.setenv("UPSCALE_SWINIR_COMMAND", "python run_swinir.py")
    monkeypatch.setenv("UPSCALE_SWINIR_MODEL_PATH", str(swinir_model))
    monkeypatch.setenv("UPSCALE_SWINIR_REPO_PATH", str(swinir_repo))
    monkeypatch.setenv("UPSCALE_HAT_BACKEND", "external")
    monkeypatch.setenv("UPSCALE_HAT_COMMAND", "python run_hat.py")
    monkeypatch.setenv("UPSCALE_HAT_MODEL_PATH", str(hat_model))
    monkeypatch.setenv("UPSCALE_HAT_REPO_PATH", str(hat_repo))
    get_settings.cache_clear()

    response = client.get("/api/upscale/models/status")

    assert response.status_code == 200
    statuses = {model["id"]: model for model in response.json()["models"]}
    assert statuses["faithful"]["status"] == "ready"
    assert statuses["faithful"]["configured"] is True
    assert statuses["swinir"]["status"] == "ready"
    assert statuses["swinir"]["configured"] is True
    assert statuses["hat"]["status"] == "ready"
    assert statuses["hat"]["configured"] is True
    get_settings.cache_clear()
