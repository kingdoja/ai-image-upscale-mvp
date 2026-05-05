from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local SwinIR real-SR inference for a single image.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--scale", required=True, type=int, choices=(2, 3, 4, 8))
    parser.add_argument("--model-path", required=True, type=Path)
    parser.add_argument("--repo-path", required=True, type=Path)
    parser.add_argument("--task", default="real_sr")
    parser.add_argument("--large-model", action="store_true")
    parser.add_argument("--tile", type=int, default=256)
    return parser.parse_args()


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

    output_dir = args.output.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    result_dir = repo_path / "results" / f"swinir_{args.task}_x{args.scale}"
    if args.large_model:
        result_dir = Path(f"{result_dir}_large")
    if result_dir.exists():
        shutil.rmtree(result_dir)

    input_dir = Path(tempfile.mkdtemp(prefix="swinir-input-"))
    copied_input = input_dir / args.input.name
    shutil.copyfile(args.input, copied_input)

    command = [
        sys.executable,
        "main_test_swinir.py",
        "--task",
        args.task,
        "--scale",
        str(args.scale),
        "--model_path",
        str(model_path),
        "--folder_lq",
        str(input_dir),
    ]
    if args.task != "real_sr":
        raise SystemExit("This wrapper currently supports real_sr only")
    if args.large_model:
        command.append("--large_model")
    if args.tile is not None:
        command.extend(["--tile", str(args.tile)])

    completed = subprocess.run(
        command,
        cwd=repo_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit((completed.stderr or completed.stdout or f"SwinIR exited with code {completed.returncode}").strip())

    candidates = sorted(result_dir.glob("*_SwinIR.png"))
    if not candidates:
        raise SystemExit("SwinIR completed without creating output")
    shutil.copyfile(candidates[0], args.output)


if __name__ == "__main__":
    main()
