from pathlib import Path
import sys

from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.evaluate_region_detector import (
    check_tesseract_available,
    evaluate_dataset,
    load_annotations,
    render_csv,
    render_markdown,
)


def _write_annotations(dataset_dir: Path) -> Path:
    annotations = dataset_dir / "annotations.json"
    annotations.write_text(
        """
{
  "samples": [
    {
      "file": "marketing-logo-only.png",
      "scene": "marketing",
      "expected_regions": ["text", "logo"],
      "expected_bboxes": {
        "logo": [40, 36, 141, 57]
      },
      "review_required": true
    },
    {
      "file": "plain-product.png",
      "scene": "product",
      "expected_regions": [],
      "review_required": false
    },
    {
      "file": "false-logo.png",
      "scene": "marketing",
      "expected_regions": [],
      "review_required": false
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )
    return annotations


def test_load_annotations_reads_samples(tmp_path):
    annotations = _write_annotations(tmp_path)

    samples = load_annotations(annotations)

    assert [sample.file for sample in samples] == ["marketing-logo-only.png", "plain-product.png", "false-logo.png"]
    assert samples[0].scene == "marketing"
    assert samples[0].expected_regions == {"text", "logo"}
    assert samples[0].expected_bboxes == {"logo": [40, 36, 141, 57]}
    assert samples[1].review_required is False


def test_checked_in_dataset_includes_text_only_and_negative_samples():
    annotations = PROJECT_ROOT / "datasets" / "region-eval" / "annotations.json"

    samples = load_annotations(annotations)
    region_sets = [sample.expected_regions for sample in samples]

    assert {"text"} in region_sets
    assert set() in region_sets


def test_region_eval_runner_documents_primary_report_entrypoint():
    script = PROJECT_ROOT / "scripts" / "run_region_detector_eval.ps1"

    content = script.read_text(encoding="utf-8")

    assert "region-detector-eval-tesseract-logo-baseline.md" in content
    assert "tools\\evaluate_region_detector.py" in content
    assert "tools\\logo_detector_baseline.py" in content
    assert "Open this first" in content
    assert "apps\\web\\public\\reports" in content
    assert "Copy-Item" in content


def test_evaluate_dataset_counts_missed_and_false_positive_regions(tmp_path):
    annotations = _write_annotations(tmp_path)
    logo_image = Image.new("RGB", (800, 600), color=(245, 245, 245))
    logo_draw = ImageDraw.Draw(logo_image)
    logo_draw.rectangle((40, 36, 180, 92), fill=(10, 10, 10))
    logo_image.save(tmp_path / "marketing-logo-only.png")
    Image.new("RGB", (800, 600), color=(245, 245, 245)).save(tmp_path / "plain-product.png")
    false_logo = Image.new("RGB", (800, 600), color=(245, 245, 245))
    false_draw = ImageDraw.Draw(false_logo)
    false_draw.rectangle((40, 36, 180, 92), fill=(10, 10, 10))
    false_logo.save(tmp_path / "false-logo.png")

    report = evaluate_dataset(annotations, backend="local")

    assert report.summary["sample_count"] == 3
    assert report.summary["evaluated_count"] == 3
    assert report.summary["missed_text"] == 1
    assert report.summary["missed_logo"] == 0
    assert report.summary["false_positive_logo"] == 1
    assert report.summary["precision_logo"] == 0.5
    assert report.summary["recall_logo"] == 1.0
    assert report.summary["expected_bbox_count"] == 1
    assert report.summary["matched_bbox_count"] == 1
    assert report.summary["missed_bbox_count"] == 0
    assert report.summary["bbox_match_rate"] == 1.0
    assert report.summary["expected_bbox_logo"] == 1
    assert report.summary["matched_bbox_logo"] == 1
    assert report.summary["missed_bbox_logo"] == 0
    assert report.summary["bbox_match_rate_logo"] == 1.0
    assert report.summary["expected_bbox_text"] == 0
    assert report.summary["bbox_match_rate_text"] == 0.0
    assert report.rows[0]["missed_regions"] == "text"
    assert report.rows[0]["expected_bboxes"] == "logo:40,36,141,57"
    assert report.rows[0]["bbox_ious"] == "logo:1.00"
    assert report.rows[0]["bbox_matches"] == "logo"
    assert report.rows[2]["false_positive_regions"] == "logo"


def test_evaluate_dataset_reports_bbox_misses_when_localization_is_poor(tmp_path):
    annotations = tmp_path / "annotations.json"
    annotations.write_text(
        """
{
  "samples": [
    {
      "file": "label.png",
      "scene": "marketing",
      "expected_regions": ["logo"],
      "expected_bboxes": {"logo": [500, 400, 80, 60]}
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )
    image = Image.new("RGB", (800, 600), color=(245, 245, 245))
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 36, 180, 92), fill=(10, 10, 10))
    image.save(tmp_path / "label.png")

    report = evaluate_dataset(annotations, backend="local")

    assert report.summary["expected_bbox_count"] == 1
    assert report.summary["matched_bbox_count"] == 0
    assert report.summary["missed_bbox_count"] == 1
    assert report.summary["bbox_match_rate"] == 0.0
    assert report.summary["expected_bbox_logo"] == 1
    assert report.summary["matched_bbox_logo"] == 0
    assert report.summary["missed_bbox_logo"] == 1
    assert report.summary["bbox_match_rate_logo"] == 0.0
    assert report.rows[0]["bbox_ious"] == "logo:0.00"
    assert report.rows[0]["bbox_matches"] == ""
    assert report.rows[0]["bbox_misses"] == "logo"


def test_evaluate_dataset_reports_missing_images(tmp_path):
    annotations = tmp_path / "annotations.json"
    annotations.write_text(
        '{"samples":[{"file":"missing.png","scene":"marketing","expected_regions":["text"]}]}',
        encoding="utf-8",
    )

    report = evaluate_dataset(annotations, backend="local")

    assert report.summary["sample_count"] == 1
    assert report.summary["evaluated_count"] == 0
    assert report.summary["missing_image_count"] == 1
    assert report.rows[0]["status"] == "missing_image"


def test_check_tesseract_available_reports_missing_command():
    availability = check_tesseract_available("definitely-missing-tesseract-command")

    assert availability["available"] is False
    assert "not available" in availability["message"]


def test_evaluate_dataset_warns_when_tesseract_backend_is_unavailable(tmp_path):
    annotations = _write_annotations(tmp_path)
    Image.new("RGB", (800, 600), color=(245, 245, 245)).save(tmp_path / "marketing-logo-only.png")
    Image.new("RGB", (800, 600), color=(245, 245, 245)).save(tmp_path / "plain-product.png")
    Image.new("RGB", (800, 600), color=(245, 245, 245)).save(tmp_path / "false-logo.png")

    report = evaluate_dataset(
        annotations,
        backend="tesseract",
        tesseract_command="definitely-missing-tesseract-command",
    )

    assert any("Tesseract is not available" in warning for warning in report.warnings)
    assert "Tesseract is not available" in render_markdown(report)


def test_evaluate_dataset_can_fuse_tesseract_with_external_logo_detector(tmp_path):
    annotations = tmp_path / "annotations.json"
    annotations.write_text(
        '{"samples":[{"file":"label.png","scene":"marketing","expected_regions":["text","logo"],"review_required":true}]}',
        encoding="utf-8",
    )
    Image.new("RGB", (800, 600), color=(245, 245, 245)).save(tmp_path / "label.png")
    tesseract = tmp_path / "fake_tesseract.py"
    tesseract.write_text(
        "\n".join(
            [
                "print('level\\tpage_num\\tblock_num\\tpar_num\\tline_num\\tword_num\\tleft\\ttop\\twidth\\theight\\tconf\\ttext')",
                "print('5\\t1\\t1\\t1\\t1\\t1\\t12\\t340\\t88\\t22\\t92\\tSALE')",
            ]
        ),
        encoding="utf-8",
    )
    logo_detector = tmp_path / "logo_detector.py"
    logo_detector.write_text(
        "\n".join(
            [
                "import json",
                "print(json.dumps({'regions': [",
                "  {'type': 'logo', 'bbox': [300, 180, 120, 90], 'confidence': 0.74}",
                "]}))",
            ]
        ),
        encoding="utf-8",
    )

    report = evaluate_dataset(
        annotations,
        backend="tesseract",
        tesseract_command=f'"{sys.executable}" "{tesseract}"',
        logo_detector_backend="external",
        logo_detector_command=f'"{sys.executable}" "{logo_detector}"',
    )

    assert report.summary["detected_text"] == 1
    assert report.summary["detected_logo"] == 1
    assert report.rows[0]["detector_sources"] == "text:tesseract_ocr;logo:logo_detector"
    assert "- logo_detector_backend: `external`" in render_markdown(report)


def test_render_region_eval_reports_include_summary_and_rows(tmp_path):
    annotations = _write_annotations(tmp_path)
    logo_image = Image.new("RGB", (800, 600), color=(245, 245, 245))
    logo_draw = ImageDraw.Draw(logo_image)
    logo_draw.rectangle((40, 36, 180, 92), fill=(10, 10, 10))
    logo_image.save(tmp_path / "marketing-logo-only.png")
    Image.new("RGB", (800, 600), color=(245, 245, 245)).save(tmp_path / "plain-product.png")
    Image.new("RGB", (800, 600), color=(245, 245, 245)).save(tmp_path / "false-logo.png")
    report = evaluate_dataset(annotations, backend="local")

    markdown = render_markdown(report)
    csv_text = render_csv(report)

    assert "# Region Detector Evaluation" in markdown
    assert "- sample_count: 3" in markdown
    assert "- bbox_match_rate: 1.0" in markdown
    assert "marketing-logo-only.png" in markdown
    assert "expected_bboxes,bbox_ious,bbox_matches,bbox_misses" in csv_text
