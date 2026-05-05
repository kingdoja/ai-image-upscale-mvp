from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
import sys
import time
from typing import Iterable, List, Optional

from fastapi import UploadFile
from PIL import Image


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


@dataclass(frozen=True)
class SmokeSample:
    path: Path
    scene: str


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def configure_imports() -> None:
    api_root = project_root() / "apps" / "api"
    for path in (project_root(), api_root):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))


def infer_scene(path: Path) -> str:
    name = path.stem.lower()
    if any(token in name for token in ("ecommerce", "detail", "logo", "text", "word", "risk")):
        return "ecommerce"
    if any(token in name for token in ("marketing", "scene", "campaign", "poster")):
        return "marketing"
    if any(token in name for token in ("white", "product", "sku")):
        return "product"
    return "other"


def discover_samples(samples_dir: Path) -> List[SmokeSample]:
    if not samples_dir.exists():
        raise FileNotFoundError(f"Samples directory does not exist: {samples_dir}")
    samples = [
        SmokeSample(path=path, scene=infer_scene(path))
        for path in sorted(samples_dir.iterdir(), key=lambda item: item.name.lower())
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    if not samples:
        raise ValueError(f"No supported images found in {samples_dir}")
    return samples


def _image_upload(path: Path) -> UploadFile:
    content_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }[path.suffix.lower()]
    return UploadFile(filename=path.name, file=BytesIO(path.read_bytes()), headers={"content-type": content_type})


def _image_size(path: str) -> str:
    with Image.open(path) as image:
        return f"{image.width}x{image.height}"


def _result_summary(results: Iterable[object]) -> str:
    parts = []
    for result in results:
        parts.append(
            (
                f"{result.result_type}: {result.model_name}/{result.model_version}, "
                f"{_image_size(result.file_path)}, risk={result.risk_level}, score={result.quality_score:.2f}"
            )
        )
    return "<br>".join(parts)


def run_samples(samples_dir: Path, output_path: Path, scale: int, mode: str, limit: Optional[int]) -> str:
    configure_imports()
    from app.config import get_settings
    from app.database import Base, SessionLocal, engine
    import app.models  # noqa: F401
    from app.jobs.service import create_feedback, create_job, process_job
    from app.schemas import FeedbackCreate

    get_settings.cache_clear()
    Base.metadata.create_all(bind=engine)

    rows = []
    samples = discover_samples(samples_dir)
    if limit is not None:
        samples = samples[:limit]

    db = SessionLocal()
    try:
        for sample in samples:
            upload = _image_upload(sample.path)
            started = time.perf_counter()
            try:
                job = create_job(db, image=upload, scale=scale, mode=mode, scene=sample.scene)
            finally:
                upload.file.close()
            completed = process_job(db, job.id)
            duration_seconds = time.perf_counter() - started
            selected_result_id = completed.results[0].id if completed.results else ""
            if selected_result_id:
                create_feedback(
                    db,
                    completed.id,
                    FeedbackCreate(
                        selected_result_id=selected_result_id,
                        rating=3,
                        usable=False,
                        issues=["other"],
                        comment="Smoke runner placeholder feedback. Replace with human review after visual inspection.",
                    ),
                )
            rows.append(
                {
                    "sample": sample.path.name,
                    "scene": sample.scene,
                    "status": completed.status,
                    "duration_seconds": f"{duration_seconds:.1f}",
                    "warnings": ", ".join(completed.warnings) or "-",
                    "results": _result_summary(completed.results) or "-",
                    "selected_result_id": selected_result_id,
                }
            )
    finally:
        db.close()

    report = build_markdown_report(samples_dir=samples_dir, rows=rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return report


def build_markdown_report(samples_dir: Path, rows: List[dict]) -> str:
    completed = sum(1 for row in rows if row["status"] == "completed")
    terminal = sum(1 for row in rows if row["status"] in {"completed", "failed"})
    high_risk_rows = [
        row
        for row in rows
        if row["scene"] in {"marketing", "ecommerce"} or row["warnings"] not in {"", "-"}
    ]
    lines = [
        "# PixelLift AI 高清放大 10 张冒烟评测报告",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"样本目录：`{samples_dir}`",
        "",
        "## 自动执行摘要",
        "",
        f"- 样本数：{len(rows)}",
        f"- completed：{completed}",
        f"- 进入终态：{terminal}",
        f"- 高风险/需人工关注样本：{len(high_risk_rows)}",
        "",
        "## 自动执行结果",
        "",
        "| 样本 | 场景 | 状态 | 耗时 | Warning | 结果 | 人工结论 |",
        "|---|---|---:|---:|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {sample} | {scene} | {status} | {duration_seconds}s | {warnings} | {results} | 待评审 |".format(**row)
        )

    lines.extend(
        [
            "",
            "## 人工评审记录",
            "",
        ]
    )
    for index, row in enumerate(rows, start=1):
        lines.extend(
            [
                f"### {index}. {row['sample']}",
                "",
                f"- 图片类型：{row['scene']}",
                "- 倍率：4x",
                "- 模式：both",
                f"- 任务状态：{row['status']}",
                f"- 最佳结果 ID：{row['selected_result_id'] or '待选择'}",
                "- 清晰度评分：",
                "- 真实感评分：",
                "- 产品一致性评分：",
                "- Logo/文字评分：",
                "- 可用性评分：",
                "- 问题标签：",
                "- 评审备注：",
                "",
            ]
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PixelLift AI smoke acceptance against a directory of sample images.")
    parser.add_argument("--samples-dir", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("tests/acceptance/smoke-report.md"))
    parser.add_argument("--scale", type=int, default=4, choices=(2, 4))
    parser.add_argument("--mode", default="both", choices=("faithful", "realistic", "both"))
    parser.add_argument("--limit", type=int, default=10)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_samples(args.samples_dir, args.output, args.scale, args.mode, args.limit)
    print(f"Smoke acceptance report written to {args.output}")


if __name__ == "__main__":
    main()
