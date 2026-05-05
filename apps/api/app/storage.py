from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import hashlib
import shutil
from typing import Optional, Tuple

from fastapi import HTTPException, UploadFile
from PIL import Image

from .config import get_settings


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


@dataclass(frozen=True)
class StoredUpload:
    path: Path
    sha256: str
    extension: str
    size_bytes: int


def ensure_storage_dirs(root: Optional[Path] = None) -> None:
    storage_root = root or get_settings().storage_root
    for folder in ("originals", "results", "thumbnails"):
        (storage_root / folder).mkdir(parents=True, exist_ok=True)


def _extension(filename: str) -> str:
    return Path(filename or "").suffix.lower()


def validate_upload_metadata(filename: str, content_type: Optional[str], size_bytes: int) -> str:
    ext = _extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported image extension")
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported image content type")
    if size_bytes <= 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if size_bytes > get_settings().max_upload_bytes:
        raise HTTPException(status_code=413, detail="Uploaded file is larger than 20MB")
    return ext


def _dated_path(root: Path, category: str, identifier: str, extension: str) -> Path:
    now = datetime.utcnow()
    return root / category / f"{now.year:04d}" / f"{now.month:02d}" / f"{identifier}{extension}"


def save_upload(upload: UploadFile, job_id: str, root: Optional[Path] = None) -> StoredUpload:
    storage_root = root or get_settings().storage_root
    ensure_storage_dirs(storage_root)
    try:
        data = upload.file.read()
        ext = validate_upload_metadata(upload.filename or "", upload.content_type, len(data))
        digest = hashlib.sha256(data).hexdigest()
        destination = _dated_path(storage_root, "originals", job_id, ext)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return StoredUpload(path=destination, sha256=digest, extension=ext, size_bytes=len(data))
    finally:
        upload.file.close()


def result_path(result_id: str, root: Optional[Path] = None) -> Path:
    storage_root = root or get_settings().storage_root
    ensure_storage_dirs(storage_root)
    path = _dated_path(storage_root, "results", result_id, ".png")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def thumbnail_path(result_id: str, root: Optional[Path] = None) -> Path:
    storage_root = root or get_settings().storage_root
    ensure_storage_dirs(storage_root)
    path = _dated_path(storage_root, "thumbnails", f"{result_id}.thumb", ".jpg")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def create_thumbnail(source: Path, destination: Path, max_size: Tuple[int, int] = (640, 640)) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        image.thumbnail(max_size)
        image.convert("RGB").save(destination, format="JPEG", quality=88)


def copy_as_result(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
