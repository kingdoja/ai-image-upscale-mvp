from pathlib import Path
import sys

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.run_smoke_acceptance import (
    build_markdown_report,
    discover_samples,
    infer_scene,
)


def test_infer_scene_from_filename():
    assert infer_scene(Path("white-product.png")) == "product"
    assert infer_scene(Path("summer-marketing-scene.jpg")) == "marketing"
    assert infer_scene(Path("ecommerce-detail.webp")) == "ecommerce"
    assert infer_scene(Path("logo-text-risk.png")) == "ecommerce"


def test_discover_samples_returns_supported_images_in_name_order(tmp_path):
    Image.new("RGB", (8, 8), color="white").save(tmp_path / "b-product.png")
    Image.new("RGB", (8, 8), color="white").save(tmp_path / "a-product.jpg")
    (tmp_path / "notes.txt").write_text("ignore", encoding="utf-8")

    samples = discover_samples(tmp_path)

    assert [sample.path.name for sample in samples] == ["a-product.jpg", "b-product.png"]
    assert [sample.scene for sample in samples] == ["product", "product"]


def test_build_markdown_report_contains_summary_and_manual_review_placeholders(tmp_path):
    report = build_markdown_report(
        samples_dir=tmp_path,
        rows=[
            {
                "sample": "logo-text-risk.png",
                "scene": "ecommerce",
                "status": "completed",
                "duration_seconds": "1.2",
                "warnings": "text_or_logo_review_recommended",
                "results": "faithful: realesrgan/realesrgan-x4plus, 128x96, risk=medium",
                "selected_result_id": "",
            }
        ],
    )

    assert "# PixelLift AI 高清放大 10 张冒烟评测报告" in report
    assert "| 样本 | 场景 | 状态 | 耗时 | Warning | 结果 | 人工结论 |" in report
    assert "logo-text-risk.png" in report
    assert "清晰度评分" in report
    assert "Logo/文字评分" in report
