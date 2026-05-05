from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local HAT inference for a single image.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--scale", required=True, type=int, choices=(2, 3, 4))
    parser.add_argument("--model-path", required=True, type=Path)
    parser.add_argument("--repo-path", required=True, type=Path)
    parser.add_argument("--opt", default="options/test/HAT_GAN_Real_SRx4.yml")
    return parser.parse_args()


def _rewrite_option_file(repo_path: Path, opt_name: str, model_path: Path, results_root: Path) -> Path:
    source = repo_path / opt_name
    if not source.exists():
        raise SystemExit(f"Base option file does not exist: {source}")

    content = source.read_text(encoding="utf-8")
    repo_posix = str(repo_path).replace("\\", "/")
    model_posix = str(model_path).replace("\\", "/")
    results_posix = str(results_root).replace("\\", "/")
    vis_posix = str(results_root / "visualization").replace("\\", "/")
    input_posix = str(repo_path / "input_dir").replace("\\", "/")

    content = content.replace("num_gpu: 1", "num_gpu: 0")
    content = re.sub(r"tile_size: \d+", "tile_size: 128", content)
    content = re.sub(r"tile_pad: \d+", "tile_pad: 16", content)
    content = content.replace("input_dir", input_posix)
    content = content.replace("./experiments/pretrained_models/Real_HAT_GAN_SRx4.pth", model_posix)
    content = content.replace("./experiments/pretrained_models/HAT_SRx4_ImageNet-pretrain.pth", model_posix)
    content = content.replace("experiments/pretrained_models/HAT_SRx4_ImageNet-pretrain.pth", model_posix)
    content = content.replace(
        f"results_root: {repo_posix}/results/HAT_GAN_Real_SRx4",
        f"results_root: {results_posix}",
    )
    content = content.replace(
        f"log: {repo_posix}/results/HAT_GAN_Real_SRx4",
        f"log: {results_posix}",
    )
    content = content.replace(
        f"visualization: {repo_posix}/results/HAT_GAN_Real_SRx4/visualization",
        f"visualization: {vis_posix}",
    )

    temp_dir = Path(tempfile.mkdtemp(prefix="hat-opt-"))
    rewritten = temp_dir / source.name
    rewritten.write_text(content, encoding="utf-8")
    return rewritten


def _create_directory_junction(alias_path: Path, target_path: Path) -> None:
    if alias_path.exists():
        return
    alias_path.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(alias_path), str(target_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or f"mklink exited with code {completed.returncode}").strip()
        raise SystemExit(f"Failed to create ASCII repo alias: {message}")


def main() -> None:
    args = parse_args()
    if not args.input.exists():
        raise SystemExit(f"Input image does not exist: {args.input}")
    if not args.model_path.exists():
        raise SystemExit(f"Model path does not exist: {args.model_path}")
    if not args.repo_path.exists():
        raise SystemExit(f"Repo path does not exist: {args.repo_path}")

    model_path = args.model_path.resolve()
    repo_path = args.repo_path.resolve()
    results_root = Path(tempfile.mkdtemp(prefix="hat-results-"))
    alias_repo = Path(tempfile.mkdtemp(prefix="hat-run-")) / "repo"
    _create_directory_junction(alias_repo, repo_path)

    temp_input_dir = alias_repo / "input_dir"
    temp_results_dir = alias_repo / "results"
    if temp_input_dir.exists():
        shutil.rmtree(temp_input_dir)
    if temp_results_dir.exists():
        shutil.rmtree(temp_results_dir)
    temp_input_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.input, temp_input_dir / args.input.name)

    rewritten_opt = _rewrite_option_file(alias_repo, args.opt, model_path, results_root)
    command = [sys.executable, "hat/test.py", "-opt", str(rewritten_opt)]
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(alias_repo) if not existing_pythonpath else f"{alias_repo}{os.pathsep}{existing_pythonpath}"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    completed = subprocess.run(
        command,
        cwd=alias_repo,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit((completed.stderr or completed.stdout or f"HAT exited with code {completed.returncode}").strip())

    candidates = sorted(alias_repo.rglob("results/**/*.png"))
    if not candidates:
        raise SystemExit("HAT completed without creating output")
    shutil.copyfile(candidates[0], args.output)


if __name__ == "__main__":
    main()
