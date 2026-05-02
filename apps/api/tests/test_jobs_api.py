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
