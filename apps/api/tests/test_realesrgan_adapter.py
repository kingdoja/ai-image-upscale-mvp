import sys
import textwrap

import pytest
from PIL import Image

from app.inference.base import ModelConfigurationError
from app.inference.realesrgan import RealESRGANAdapter


def test_realesrgan_adapter_requires_executable(tmp_path):
    input_path = tmp_path / "input.png"
    output_path = tmp_path / "output.png"
    Image.new("RGB", (8, 8), color="white").save(input_path)

    adapter = RealESRGANAdapter()

    with pytest.raises(ModelConfigurationError, match="executable is not configured"):
        adapter.upscale(input_path, output_path, 4)


def test_realesrgan_adapter_runs_external_command(tmp_path):
    fake_cli = tmp_path / "fake_realesrgan.py"
    fake_cli.write_text(
        textwrap.dedent(
            """
            import argparse
            from PIL import Image

            parser = argparse.ArgumentParser()
            parser.add_argument("-i", required=True)
            parser.add_argument("-o", required=True)
            parser.add_argument("-s", type=int, required=True)
            parser.add_argument("-m", required=True)
            parser.add_argument("-n", required=True)
            args = parser.parse_args()

            with Image.open(args.i) as image:
                width, height = image.size
                image.resize((width * args.s, height * args.s)).save(args.o)
            """
        ),
        encoding="utf-8",
    )
    input_path = tmp_path / "input.png"
    output_path = tmp_path / "output.png"
    Image.new("RGB", (8, 5), color="white").save(input_path)
    adapter = RealESRGANAdapter(
        executable_path=sys.executable,
        model_path=tmp_path,
        model="fake-x4",
        prefix_args=[str(fake_cli)],
        timeout_seconds=10,
    )

    output = adapter.upscale(input_path, output_path, 4)

    assert output.model_name == "realesrgan"
    assert output.model_version == "fake-x4"
    with Image.open(output_path) as image:
        assert image.size == (32, 20)
