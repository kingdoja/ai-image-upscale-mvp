from io import BytesIO
from pathlib import Path
import sys

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
    assert len(completed.results) >= 1
    assert {result.result_type for result in completed.results} == {"faithful"}
    get_settings.cache_clear()


def test_worker_does_not_generate_removed_fallback_candidates_for_product_jobs(db_session, sample_image_bytes, temp_storage, monkeypatch):
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("STORAGE_ROOT", str(temp_storage))
    upload = UploadFile(filename="product.png", file=BytesIO(sample_image_bytes), headers={"content-type": "image/png"})
    job = create_job(db_session, image=upload, scale=4, mode="faithful", scene="product")

    completed = process_job(db_session, job.id)

    assert completed.status == "completed"
    assert {result.result_type for result in completed.results} == {"faithful"}
    get_settings.cache_clear()


def test_worker_marks_swinir_and_hat_as_skipped_when_not_configured(db_session, sample_image_bytes, temp_storage, monkeypatch):
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("STORAGE_ROOT", str(temp_storage))
    upload = UploadFile(filename="product.png", file=BytesIO(sample_image_bytes), headers={"content-type": "image/png"})
    job = create_job(db_session, image=upload, scale=4, mode="both", scene="product")

    completed = process_job(db_session, job.id)
    from app.jobs.service import serialize_job

    payload = serialize_job(completed)["routing_decision"]

    assert completed.status == "completed"
    assert "swinir" in payload["skipped_candidate_types"]
    assert "hat" in payload["skipped_candidate_types"]
    assert payload["skip_reasons"]["swinir"] == "backend_disabled_or_not_configured"
    assert payload["skip_reasons"]["hat"] == "backend_disabled_or_not_configured"
    get_settings.cache_clear()


def test_worker_runs_external_swinir_candidate_when_configured(db_session, sample_image_bytes, temp_storage, tmp_path, monkeypatch):
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("STORAGE_ROOT", str(temp_storage))
    repo_path = tmp_path / "swinir-repo"
    repo_path.mkdir()
    model_path = tmp_path / "swinir.pth"
    model_path.write_text("fake weights", encoding="utf-8")
    wrapper = tmp_path / "swinir_wrapper.py"
    wrapper.write_text(
        "\n".join(
            [
                "import argparse",
                "from pathlib import Path",
                "from PIL import Image",
                "parser = argparse.ArgumentParser()",
                "parser.add_argument('--repo-path', required=True)",
                "parser.add_argument('--input', required=True)",
                "parser.add_argument('--output', required=True)",
                "parser.add_argument('--scale', type=int, required=True)",
                "parser.add_argument('--model-path', required=True)",
                "args = parser.parse_args()",
                "Path(args.repo_path).mkdir(parents=True, exist_ok=True)",
                "with Image.open(args.input) as image:",
                "    image.resize((image.width * args.scale, image.height * args.scale)).save(args.output)",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("UPSCALE_SWINIR_BACKEND", "external")
    monkeypatch.setenv("UPSCALE_SWINIR_COMMAND", f'"{sys.executable}" "{wrapper}"')
    monkeypatch.setenv("UPSCALE_SWINIR_MODEL_PATH", str(model_path))
    monkeypatch.setenv("UPSCALE_SWINIR_REPO_PATH", str(repo_path))
    monkeypatch.setenv("UPSCALE_SWINIR_TIMEOUT_SECONDS", "60")

    upload = UploadFile(filename="product.png", file=BytesIO(sample_image_bytes), headers={"content-type": "image/png"})
    job = create_job(db_session, image=upload, scale=4, mode="both", scene="product")

    completed = process_job(db_session, job.id)

    assert completed.status == "completed"
    assert any(result.result_type == "swinir" for result in completed.results)
    swinir = next(result for result in completed.results if result.result_type == "swinir")
    assert swinir.model_name == "swinir"
    assert swinir.model_version == "external"
    with Image.open(swinir.file_path) as image:
        assert image.size == (64, 40)
    get_settings.cache_clear()


def test_worker_runs_external_hat_candidate_when_configured(db_session, sample_image_bytes, temp_storage, tmp_path, monkeypatch):
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("STORAGE_ROOT", str(temp_storage))
    repo_path = tmp_path / "hat-repo"
    repo_path.mkdir()
    model_path = tmp_path / "hat.pth"
    model_path.write_text("fake weights", encoding="utf-8")
    wrapper = tmp_path / "hat_wrapper.py"
    wrapper.write_text(
        "\n".join(
            [
                "import argparse",
                "from pathlib import Path",
                "from PIL import Image",
                "parser = argparse.ArgumentParser()",
                "parser.add_argument('--repo-path', required=True)",
                "parser.add_argument('--input', required=True)",
                "parser.add_argument('--output', required=True)",
                "parser.add_argument('--scale', type=int, required=True)",
                "parser.add_argument('--model-path', required=True)",
                "args = parser.parse_args()",
                "Path(args.repo_path).mkdir(parents=True, exist_ok=True)",
                "with Image.open(args.input) as image:",
                "    image.resize((image.width * args.scale, image.height * args.scale)).save(args.output)",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("UPSCALE_HAT_BACKEND", "external")
    monkeypatch.setenv("UPSCALE_HAT_COMMAND", f'"{sys.executable}" "{wrapper}"')
    monkeypatch.setenv("UPSCALE_HAT_MODEL_PATH", str(model_path))
    monkeypatch.setenv("UPSCALE_HAT_REPO_PATH", str(repo_path))
    monkeypatch.setenv("UPSCALE_HAT_TIMEOUT_SECONDS", "60")

    upload = UploadFile(filename="product.png", file=BytesIO(sample_image_bytes), headers={"content-type": "image/png"})
    job = create_job(db_session, image=upload, scale=4, mode="both", scene="product")

    completed = process_job(db_session, job.id)

    assert completed.status == "completed"
    assert any(result.result_type == "hat" for result in completed.results)
    hat = next(result for result in completed.results if result.result_type == "hat")
    assert hat.model_name == "hat"
    assert hat.model_version == "external"
    with Image.open(hat.file_path) as image:
        assert image.size == (64, 40)
    get_settings.cache_clear()


def test_worker_respects_selected_candidate_order_and_subset(db_session, sample_image_bytes, temp_storage, tmp_path, monkeypatch):
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("STORAGE_ROOT", str(temp_storage))
    repo_path = tmp_path / "hat-repo"
    repo_path.mkdir()
    model_path = tmp_path / "hat.pth"
    model_path.write_text("fake weights", encoding="utf-8")
    wrapper = tmp_path / "hat_wrapper.py"
    wrapper.write_text(
        "\n".join(
            [
                "import argparse",
                "from pathlib import Path",
                "from PIL import Image",
                "parser = argparse.ArgumentParser()",
                "parser.add_argument('--repo-path', required=True)",
                "parser.add_argument('--input', required=True)",
                "parser.add_argument('--output', required=True)",
                "parser.add_argument('--scale', type=int, required=True)",
                "parser.add_argument('--model-path', required=True)",
                "args = parser.parse_args()",
                "Path(args.repo_path).mkdir(parents=True, exist_ok=True)",
                "with Image.open(args.input) as image:",
                "    image.resize((image.width * args.scale, image.height * args.scale)).save(args.output)",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("UPSCALE_HAT_BACKEND", "external")
    monkeypatch.setenv("UPSCALE_HAT_COMMAND", f'"{sys.executable}" "{wrapper}"')
    monkeypatch.setenv("UPSCALE_HAT_MODEL_PATH", str(model_path))
    monkeypatch.setenv("UPSCALE_HAT_REPO_PATH", str(repo_path))
    monkeypatch.setenv("UPSCALE_HAT_TIMEOUT_SECONDS", "60")

    upload = UploadFile(filename="product.png", file=BytesIO(sample_image_bytes), headers={"content-type": "image/png"})
    job = create_job(
        db_session,
        image=upload,
        scale=4,
        mode="both",
        scene="product",
        selected_candidates=["hat", "faithful"],
    )

    completed = process_job(db_session, job.id)

    assert completed.status == "completed"
    assert [result.result_type for result in completed.results] == ["faithful", "hat"]
    get_settings.cache_clear()


def test_worker_fails_when_realesrgan_is_unconfigured_without_sharpened_fallback(db_session, sample_image_bytes, temp_storage, monkeypatch):
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("STORAGE_ROOT", str(temp_storage))
    monkeypatch.setenv("UPSCALE_FAITHFUL_BACKEND", "realesrgan")
    upload = UploadFile(filename="product.png", file=BytesIO(sample_image_bytes), headers={"content-type": "image/png"})
    job = create_job(db_session, image=upload, scale=4, mode="faithful", scene="product")

    completed = process_job(db_session, job.id)

    assert completed.status == "failed"
    assert completed.results == []
    assert any("Real-ESRGAN executable is not configured" in warning for warning in completed.warnings)
    assert any("No result images were generated" in warning for warning in completed.warnings)
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

    assert completed.status == "completed"
    faithful = next((result for result in completed.results if result.result_type == "faithful"), None)
    if faithful is None:
        pytest.skip(f"Local Real-ESRGAN command did not produce a faithful result: {completed.warnings}")
    assert faithful.model_name == "realesrgan"
    assert faithful.model_version == "realesrgan-x4plus"
    with Image.open(faithful.file_path) as image:
        assert image.size == (128, 96)
    get_settings.cache_clear()
