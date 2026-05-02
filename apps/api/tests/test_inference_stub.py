from pathlib import Path

from PIL import Image

from app.inference.stub import StubUpscaleAdapter


def test_stub_adapter_creates_scaled_png(tmp_path):
    input_path = tmp_path / "input.png"
    output_path = tmp_path / "output.png"
    Image.new("RGB", (12, 8), color="blue").save(input_path)

    output = StubUpscaleAdapter().upscale(input_path, output_path, 4)

    assert output.output_path == output_path
    assert output.model_name == "pillow-stub-upscale"
    with Image.open(output_path) as image:
        assert image.size == (48, 32)
