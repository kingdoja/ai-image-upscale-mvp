from pathlib import Path
import shlex
import subprocess
import time
from typing import List, Optional

from PIL import Image

from .base import ModelConfigurationError, UpscaleOutput


class OptionalModelAdapter:
    def __init__(self, model_name: str, model_version: str = "unconfigured", enabled: bool = False) -> None:
        self.model_name = model_name
        self.model_version = model_version
        self.enabled = enabled

    def upscale(self, input_path: Path, output_path: Path, scale: int) -> UpscaleOutput:
        if not self.enabled:
            raise ModelConfigurationError(f"{self.model_name} backend is not configured")
        raise ModelConfigurationError(f"{self.model_name} runtime integration is not enabled in stub mode")


class DisabledOptionalModelAdapter:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.model_version = "disabled"

    def upscale(self, input_path: Path, output_path: Path, scale: int) -> UpscaleOutput:
        raise ModelConfigurationError(f"{self.model_name} backend is not configured")


class ExternalUpscaleAdapter:
    def __init__(
        self,
        *,
        model_name: str,
        model_version: str,
        command: str,
        model_path: Optional[Path],
        extra_args: Optional[List[str]] = None,
        timeout_seconds: int = 600,
    ) -> None:
        self.model_name = model_name
        self.model_version = model_version
        self.command = command
        self.model_path = Path(model_path) if model_path else None
        self.extra_args = list(extra_args or [])
        self.timeout_seconds = timeout_seconds

    def upscale(self, input_path: Path, output_path: Path, scale: int) -> UpscaleOutput:
        if not self.command:
            raise ModelConfigurationError(f"{self.model_name} command is not configured")
        if not self.model_path or not self.model_path.exists():
            raise ModelConfigurationError(f"{self.model_name} model path is not configured")
        if not input_path.exists():
            raise ModelConfigurationError(f"{self.model_name} input image does not exist")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            *shlex.split(self.command),
            *self.extra_args,
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--scale",
            str(scale),
            "--model-path",
            str(self.model_path),
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
            raise ModelConfigurationError(f"{self.model_name} command timed out") from exc
        except OSError as exc:
            raise ModelConfigurationError(f"{self.model_name} command failed to start: {exc}") from exc

        if completed.returncode != 0:
            message = self._summarize_command_error(completed.stderr or completed.stdout or "")
            if not message:
                message = f"exit code {completed.returncode}"
            raise ModelConfigurationError(f"{self.model_name} command failed: {message}")
        if not output_path.exists():
            raise ModelConfigurationError(f"{self.model_name} command completed without creating output")
        self._validate_output_image(input_path, output_path, scale)

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return UpscaleOutput(
            output_path=output_path,
            model_name=self.model_name,
            model_version=self.model_version,
            scale=scale,
            elapsed_ms=elapsed_ms,
            warnings=[],
        )

    def _validate_output_image(self, input_path: Path, output_path: Path, scale: int) -> None:
        try:
            with Image.open(input_path) as input_image:
                expected_size = (input_image.width * scale, input_image.height * scale)
            with Image.open(output_path) as image:
                image.verify()
            with Image.open(output_path) as image:
                if image.size != expected_size:
                    raise ModelConfigurationError(
                        f"{self.model_name} output has unexpected output dimensions: expected {expected_size}, got {image.size}"
                    )
        except OSError as exc:
            raise ModelConfigurationError(f"{self.model_name} output is not a readable image: {exc}") from exc

    def _summarize_command_error(self, output: str) -> str:
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        for line in reversed(lines):
            if any(marker in line for marker in ("RuntimeError:", "UnboundLocalError:", "AssertionError:", "OSError:", "MemoryError:")):
                return line[:500]
        for line in reversed(lines):
            if "exited with code" in line or "not enough memory" in line:
                return line[:500]
        return output.strip()[:500]
