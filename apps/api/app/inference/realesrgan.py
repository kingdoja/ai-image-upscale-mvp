from pathlib import Path
import subprocess
import time
from typing import List, Optional

from PIL import Image, ImageStat

from .base import ModelConfigurationError, UpscaleOutput


class RealESRGANAdapter:
    model_name = "realesrgan"
    model_version = "ncnn-vulkan-cli"

    def __init__(
        self,
        executable_path: Optional[Path] = None,
        model_path: Optional[Path] = None,
        model: str = "realesrgan-x4plus",
        timeout_seconds: int = 300,
        prefix_args: Optional[List[str]] = None,
    ) -> None:
        self.executable_path = Path(executable_path) if executable_path else None
        self.model_path = Path(model_path) if model_path else None
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.prefix_args = prefix_args or []

    def upscale(self, input_path: Path, output_path: Path, scale: int) -> UpscaleOutput:
        if scale not in {2, 4}:
            raise ModelConfigurationError("Real-ESRGAN adapter only supports 2x or 4x scale in MVP")
        if not self.executable_path or not self.executable_path.exists():
            raise ModelConfigurationError("Real-ESRGAN executable is not configured")
        if not input_path.exists():
            raise ModelConfigurationError("Real-ESRGAN input image does not exist")
        model_path = self.model_path or (self.executable_path.parent / "models")
        if not model_path.exists():
            raise ModelConfigurationError(f"Real-ESRGAN model path does not exist: {model_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            str(self.executable_path),
            *self.prefix_args,
            "-i",
            str(input_path),
            "-o",
            str(output_path),
            "-s",
            str(scale),
            "-m",
            str(model_path),
            "-n",
            self.model,
        ]
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        except subprocess.TimeoutExpired as exc:
            raise ModelConfigurationError("Real-ESRGAN command timed out") from exc
        except OSError as exc:
            raise ModelConfigurationError(f"Real-ESRGAN command failed to start: {exc}") from exc

        if completed.returncode != 0:
            stderr = (completed.stderr or completed.stdout or "").strip()
            message = stderr[:500] if stderr else f"exit code {completed.returncode}"
            raise ModelConfigurationError(f"Real-ESRGAN command failed: {message}")
        if not output_path.exists():
            raise ModelConfigurationError("Real-ESRGAN command completed without creating output")
        self._validate_output_image(output_path)

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return UpscaleOutput(
            output_path=output_path,
            model_name=self.model_name,
            model_version=self.model,
            scale=scale,
            elapsed_ms=elapsed_ms,
            warnings=[],
        )

    def _validate_output_image(self, output_path: Path) -> None:
        try:
            with Image.open(output_path) as image:
                rgb = image.convert("RGB")
                extrema = rgb.getextrema()
                stat = ImageStat.Stat(rgb)
        except OSError as exc:
            raise ModelConfigurationError(f"Real-ESRGAN output is not a readable image: {exc}") from exc

        channel_ranges = [high - low for low, high in extrema]
        mean_brightness = sum(stat.mean) / 3
        if max(channel_ranges) <= 1 and mean_brightness <= 2:
            raise ModelConfigurationError("Real-ESRGAN command created a blank output image")
