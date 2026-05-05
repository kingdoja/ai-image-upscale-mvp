from pathlib import Path
import sys
import textwrap

import pytest
from PIL import Image

from app.inference.base import ModelConfigurationError
from app.inference.optional_models import ExternalUpscaleAdapter


def test_external_adapter_calls_wrapper_and_records_metadata(tmp_path):
    input_path = tmp_path / "input.png"
    output_path = tmp_path / "output.png"
    model_path = tmp_path / "weights.pth"
    wrapper = tmp_path / "wrapper.py"
    Image.new("RGB", (8, 6), color=(30, 120, 200)).save(input_path)
    model_path.write_text("fake weights", encoding="utf-8")
    wrapper.write_text(
        "\n".join(
            [
                "import argparse",
                "from PIL import Image",
                "parser = argparse.ArgumentParser()",
                "parser.add_argument('--input')",
                "parser.add_argument('--output')",
                "parser.add_argument('--scale', type=int)",
                "parser.add_argument('--model-path')",
                "args = parser.parse_args()",
                "with Image.open(args.input) as image:",
                "    image.resize((image.width * args.scale, image.height * args.scale)).save(args.output)",
            ]
        ),
        encoding="utf-8",
    )

    output = ExternalUpscaleAdapter(
        model_name="swinir",
        model_version="external",
        command=f'"{sys.executable}" "{wrapper}"',
        model_path=model_path,
    ).upscale(input_path, output_path, 4)

    assert output.output_path == output_path
    assert output.model_name == "swinir"
    assert output.model_version == "external"
    assert output.warnings == []
    with Image.open(output_path) as image:
        assert image.size == (32, 24)


def test_external_adapter_passes_extra_args_to_wrapper(tmp_path):
    input_path = tmp_path / "input.png"
    output_path = tmp_path / "output.png"
    model_path = tmp_path / "weights.pth"
    repo_path = tmp_path / "repo"
    wrapper = tmp_path / "wrapper.py"
    repo_path.mkdir()
    Image.new("RGB", (8, 6), color=(30, 120, 200)).save(input_path)
    model_path.write_text("fake weights", encoding="utf-8")
    wrapper.write_text(
        textwrap.dedent(
            """
            import argparse
            from PIL import Image

            parser = argparse.ArgumentParser()
            parser.add_argument('--repo-path', required=True)
            parser.add_argument('--input', required=True)
            parser.add_argument('--output', required=True)
            parser.add_argument('--scale', type=int, required=True)
            parser.add_argument('--model-path', required=True)
            args = parser.parse_args()

            with Image.open(args.input) as image:
                image.resize((image.width * args.scale, image.height * args.scale)).save(args.output)
            """
        ),
        encoding="utf-8",
    )

    output = ExternalUpscaleAdapter(
        model_name="hat",
        model_version="external",
        command=f'"{sys.executable}" "{wrapper}"',
        model_path=model_path,
        extra_args=["--repo-path", str(repo_path)],
    ).upscale(input_path, output_path, 4)

    assert output.model_name == "hat"
    with Image.open(output_path) as image:
        assert image.size == (32, 24)


def test_external_adapter_rejects_wrong_output_dimensions(tmp_path):
    input_path = tmp_path / "input.png"
    output_path = tmp_path / "output.png"
    model_path = tmp_path / "weights.pth"
    wrapper = tmp_path / "wrapper.py"
    Image.new("RGB", (8, 6), color=(30, 120, 200)).save(input_path)
    model_path.write_text("fake weights", encoding="utf-8")
    wrapper.write_text(
        textwrap.dedent(
            """
            import argparse
            from PIL import Image

            parser = argparse.ArgumentParser()
            parser.add_argument('--input')
            parser.add_argument('--output')
            parser.add_argument('--scale', type=int)
            parser.add_argument('--model-path')
            args = parser.parse_args()

            with Image.open(args.input) as image:
                image.save(args.output)
            """
        ),
        encoding="utf-8",
    )

    adapter = ExternalUpscaleAdapter(
        model_name="swinir",
        model_version="external",
        command=f'"{sys.executable}" "{wrapper}"',
        model_path=model_path,
    )

    with pytest.raises(ModelConfigurationError, match="unexpected output dimensions"):
        adapter.upscale(input_path, output_path, 4)


def test_external_adapter_requires_command(tmp_path):
    input_path = tmp_path / "input.png"
    output_path = tmp_path / "output.png"
    model_path = tmp_path / "weights.pth"
    Image.new("RGB", (8, 6), color=(30, 120, 200)).save(input_path)
    model_path.write_text("fake weights", encoding="utf-8")

    adapter = ExternalUpscaleAdapter(
        model_name="hat",
        model_version="external",
        command="",
        model_path=model_path,
    )

    with pytest.raises(ModelConfigurationError, match="hat command is not configured"):
        adapter.upscale(input_path, output_path, 4)


def test_external_adapter_fails_when_wrapper_does_not_write_output(tmp_path):
    input_path = tmp_path / "input.png"
    output_path = tmp_path / "output.png"
    model_path = tmp_path / "weights.pth"
    wrapper = tmp_path / "wrapper.py"
    Image.new("RGB", (8, 6), color=(30, 120, 200)).save(input_path)
    model_path.write_text("fake weights", encoding="utf-8")
    wrapper.write_text("import sys; sys.exit(0)", encoding="utf-8")

    adapter = ExternalUpscaleAdapter(
        model_name="swinir",
        model_version="external",
        command=f'"{sys.executable}" "{wrapper}"',
        model_path=model_path,
    )

    with pytest.raises(ModelConfigurationError, match="completed without creating output"):
        adapter.upscale(input_path, output_path, 4)


def test_external_adapter_summarizes_long_wrapper_errors(tmp_path):
    input_path = tmp_path / "input.png"
    output_path = tmp_path / "output.png"
    model_path = tmp_path / "weights.pth"
    wrapper = tmp_path / "wrapper.py"
    Image.new("RGB", (8, 6), color=(30, 120, 200)).save(input_path)
    model_path.write_text("fake weights", encoding="utf-8")
    wrapper.write_text(
        "\n".join(
            [
                "import sys",
                "print('UserWarning: noisy dependency warning', file=sys.stderr)",
                "print('Traceback (most recent call last):', file=sys.stderr)",
                "print('RuntimeError: not enough memory: tried to allocate 123 bytes', file=sys.stderr)",
                "sys.exit(1)",
            ]
        ),
        encoding="utf-8",
    )

    adapter = ExternalUpscaleAdapter(
        model_name="hat",
        model_version="external",
        command=f'"{sys.executable}" "{wrapper}"',
        model_path=model_path,
    )

    with pytest.raises(ModelConfigurationError, match="hat command failed: RuntimeError: not enough memory"):
        adapter.upscale(input_path, output_path, 4)
