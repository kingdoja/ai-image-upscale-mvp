from pathlib import Path
from typing import List, Protocol

from pydantic import BaseModel


class ModelConfigurationError(RuntimeError):
    """Raised when a configured model backend is missing weights or settings."""


class UpscaleOutput(BaseModel):
    output_path: Path
    model_name: str
    model_version: str
    scale: int
    elapsed_ms: int
    warnings: List[str] = []


class UpscaleAdapter(Protocol):
    model_name: str
    model_version: str

    def upscale(self, input_path: Path, output_path: Path, scale: int) -> UpscaleOutput:
        ...
