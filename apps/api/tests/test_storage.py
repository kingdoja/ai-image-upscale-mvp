from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile

from app.storage import save_upload, validate_upload_metadata


def upload_file(name: str, content_type: str, data: bytes) -> UploadFile:
    return UploadFile(filename=name, file=BytesIO(data), headers={"content-type": content_type})


def test_save_upload_accepts_valid_png(sample_image_bytes, temp_storage):
    stored = save_upload(upload_file("product.png", "image/png", sample_image_bytes), "up_test", temp_storage)

    assert stored.path.exists()
    assert stored.extension == ".png"
    assert len(stored.sha256) == 64


def test_validate_upload_rejects_bad_extension():
    with pytest.raises(HTTPException) as exc:
        validate_upload_metadata("product.txt", "text/plain", 10)

    assert exc.value.status_code == 400


def test_validate_upload_rejects_empty_file():
    with pytest.raises(HTTPException) as exc:
        validate_upload_metadata("product.png", "image/png", 0)

    assert exc.value.status_code == 400


def test_validate_upload_rejects_large_file(monkeypatch):
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "5")
    with pytest.raises(HTTPException) as exc:
        validate_upload_metadata("product.png", "image/png", 6)

    assert exc.value.status_code == 413
    get_settings.cache_clear()
