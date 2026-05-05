from pathlib import Path
from typing import Optional

from .base import ModelConfigurationError, UpscaleOutput


class DiffusionUpscaleAdapter:
    model_name = "diffusion-realistic"
    model_version = "unconfigured"

    def __init__(self, checkpoint_dir: Optional[Path] = None) -> None:
        self.checkpoint_dir = checkpoint_dir

    def upscale(self, input_path: Path, output_path: Path, scale: int) -> UpscaleOutput:
        if not self.checkpoint_dir or not self.checkpoint_dir.exists():
            raise ModelConfigurationError("Diffusion checkpoint directory is not configured")
        raise ModelConfigurationError("Diffusion runtime integration is not enabled in stub mode")
