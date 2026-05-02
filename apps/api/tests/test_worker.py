from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
import pytest
from PIL import Image

from app.jobs.service import create_job, process_job


def test_worker_completes_stub_job_with_results(db_session, sample_image_bytes, temp_storage, monkeypatch):
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("STORAGE_ROOT", str(temp_storage))
    upload = UploadFile(filename="product.png", file=BytesIO(sample_image_bytes), headers={"content-type": "image/png"})
    job = create_job(db_session, image=upload, scale=4, mode="both", scene="product")

    completed = process_job(db_session, job.id)

    assert completed.status == "completed"
    assert len(completed.results) >= 2
    assert {result.result_type for result in completed.results} >= {"faithful", "sharpened"}
    get_settings.cache_clear()


def test_worker_falls_back_when_realesrgan_is_unconfigured(db_session, sample_image_bytes, temp_storage, monkeypatch):
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("STORAGE_ROOT", str(temp_storage))
    monkeypatch.setenv("UPSCALE_FAITHFUL_BACKEND", "realesrgan")
    upload = UploadFile(filename="product.png", file=BytesIO(sample_image_bytes), headers={"content-type": "image/png"})
    job = create_job(db_session, image=upload, scale=4, mode="faithful", scene="product")

    completed = process_job(db_session, job.id)

    assert completed.status == "completed"
    assert {result.result_type for result in completed.results} == {"sharpened"}
    assert any("Real-ESRGAN executable is not configured" in warning for warning in completed.warnings)
    get_settings.cache_clear()


def test_worker_completes_real_realesrgan_job_when_local_model_is_available(db_session, tmp_path, temp_storage, monkeypatch):
    from app.config import get_settings

    project_root = Path(__file__).resolve().parents[3]
    executable = project_root / "models" / "realesrgan" / "realesrgan-ncnn-vulkan.exe"
    model_path = project_root / "models" / "realesrgan" / "models"
    if not executable.exists() or not (model_path / "realesrgan-x4plus.param").exists():
        pytest.skip("Local Real-ESRGAN executable and model files are not installed")

    get_settings.cache_clear()
    monkeypatch.setenv("STORAGE_ROOT", str(temp_storage))
    monkeypatch.setenv("UPSCALE_FAITHFUL_BACKEND", "realesrgan")
    monkeypatch.setenv("REALESRGAN_EXECUTABLE", str(executable))
    monkeypatch.setenv("REALESRGAN_MODEL_PATH", str(model_path))
    monkeypatch.setenv("REALESRGAN_MODEL", "realesrgan-x4plus")
    monkeypatch.setenv("REALESRGAN_TIMEOUT_SECONDS", "60")

    input_path = tmp_path / "product.png"
    Image.new("RGB", (32, 24), color=(30, 120, 200)).save(input_path)
    upload = UploadFile(
        filename="product.png",
        file=input_path.open("rb"),
        headers={"content-type": "image/png"},
    )

    try:
        job = create_job(db_session, image=upload, scale=4, mode="faithful", scene="product")
    finally:
        upload.file.close()

    completed = process_job(db_session, job.id)

    faithful = next(result for result in completed.results if result.result_type == "faithful")
    assert completed.status == "completed"
    assert faithful.model_name == "realesrgan"
    assert faithful.model_version == "realesrgan-x4plus"
    with Image.open(faithful.file_path) as image:
        assert image.size == (128, 96)
    get_settings.cache_clear()
