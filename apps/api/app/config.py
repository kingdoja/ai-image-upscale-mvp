from functools import lru_cache
from pathlib import Path
import os

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    service_name: str = "pixel-lift-api"
    database_url: str = Field(default="sqlite:///./upscale.db", env="DATABASE_URL")
    storage_root: Path = Field(default=Path("../../storage"), env="STORAGE_ROOT")
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    enqueue_jobs: bool = Field(default=False, env="ENQUEUE_JOBS")
    process_inline: bool = Field(default=False, env="UPSCALE_PROCESS_INLINE")
    max_upload_bytes: int = Field(default=20 * 1024 * 1024, env="MAX_UPLOAD_BYTES")
    max_input_pixels: int = Field(default=12_000_000, env="UPSCALE_MAX_INPUT_PIXELS")
    faithful_backend: str = Field(default="stub", env="UPSCALE_FAITHFUL_BACKEND")
    realistic_backend: str = Field(default="disabled", env="UPSCALE_REALISTIC_BACKEND")
    swinir_backend: str = Field(default="disabled", env="UPSCALE_SWINIR_BACKEND")
    swinir_command: str = Field(default="", env="UPSCALE_SWINIR_COMMAND")
    swinir_model_path: str = Field(default="", env="UPSCALE_SWINIR_MODEL_PATH")
    swinir_repo_path: str = Field(default="", env="UPSCALE_SWINIR_REPO_PATH")
    swinir_timeout_seconds: int = Field(default=600, env="UPSCALE_SWINIR_TIMEOUT_SECONDS")
    hat_backend: str = Field(default="disabled", env="UPSCALE_HAT_BACKEND")
    hat_command: str = Field(default="", env="UPSCALE_HAT_COMMAND")
    hat_model_path: str = Field(default="", env="UPSCALE_HAT_MODEL_PATH")
    hat_repo_path: str = Field(default="", env="UPSCALE_HAT_REPO_PATH")
    hat_timeout_seconds: int = Field(default=600, env="UPSCALE_HAT_TIMEOUT_SECONDS")
    region_detector_backend: str = Field(default="local", env="UPSCALE_REGION_DETECTOR_BACKEND")
    region_detector_command: str = Field(default="", env="UPSCALE_REGION_DETECTOR_COMMAND")
    region_detector_timeout_seconds: int = Field(default=30, env="UPSCALE_REGION_DETECTOR_TIMEOUT_SECONDS")
    tesseract_command: str = Field(default="tesseract", env="UPSCALE_TESSERACT_COMMAND")
    logo_detector_backend: str = Field(default="local", env="UPSCALE_LOGO_DETECTOR_BACKEND")
    logo_detector_command: str = Field(default="", env="UPSCALE_LOGO_DETECTOR_COMMAND")
    realesrgan_executable: str = Field(default="", env="REALESRGAN_EXECUTABLE")
    realesrgan_model_path: str = Field(default="", env="REALESRGAN_MODEL_PATH")
    realesrgan_model: str = Field(default="realesrgan-x4plus", env="REALESRGAN_MODEL")
    realesrgan_timeout_seconds: int = Field(default=300, env="REALESRGAN_TIMEOUT_SECONDS")

    class Config:
        env_file = ".env"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    override_root = os.getenv("STORAGE_ROOT")
    if override_root:
        settings.storage_root = Path(override_root)
    return settings
