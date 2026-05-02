from pathlib import Path
import time

from PIL import Image, ImageFilter

from .base import UpscaleOutput


class StubUpscaleAdapter:
    model_name = "pillow-stub-upscale"
    model_version = "0.1.0"

    def __init__(self, sharpen: bool = True) -> None:
        self.sharpen = sharpen

    def upscale(self, input_path: Path, output_path: Path, scale: int) -> UpscaleOutput:
        started = time.perf_counter()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(input_path) as image:
            width, height = image.size
            resized = image.resize((width * scale, height * scale), Image.Resampling.LANCZOS)
            if self.sharpen:
                resized = resized.filter(ImageFilter.SHARPEN)
            resized.save(output_path, format="PNG")
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return UpscaleOutput(
            output_path=output_path,
            model_name=self.model_name,
            model_version=self.model_version,
            scale=scale,
            elapsed_ms=elapsed_ms,
            warnings=["stub_adapter_used"],
        )
