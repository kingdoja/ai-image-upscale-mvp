import json
import sys

from PIL import Image, ImageDraw

from app.semantic_controller import (
    build_routing_decision,
    create_upscale_plan,
    get_model_capability_registry,
    understand_image,
)


def test_product_image_understanding_is_low_risk(tmp_path):
    input_path = tmp_path / "product.png"
    Image.new("RGB", (32, 24), color=(40, 120, 200)).save(input_path)

    report = understand_image(input_path, scene="product")

    assert report.scene == "product"
    assert report.review_required is False
    assert report.controller_version == "semantic-controller-v0.10.0"
    assert report.data_usage_policy == "inference_only"
    assert report.image_width == 32
    assert report.image_height == 24
    assert "low_resolution_input" in report.degradation_types
    assert report.detected_risks == []
    assert "generic_product_subject" in report.subject_hints


def test_marketing_understanding_requires_logo_and_text_review(tmp_path):
    input_path = tmp_path / "poster.png"
    Image.new("RGB", (800, 600), color=(220, 220, 210)).save(input_path)

    report = understand_image(input_path, scene="marketing")

    assert report.review_required is True
    assert "text_region_requires_review" in report.detected_risks
    assert "logo_region_requires_review" in report.detected_risks
    assert "marketing_layout" in report.subject_hints
    assert report.image_width == 800
    assert report.image_height == 600


def test_high_risk_plan_keeps_faithful_candidate_before_realistic(tmp_path):
    input_path = tmp_path / "detail.png"
    Image.new("RGB", (800, 600), color=(220, 220, 220)).save(input_path)
    report = understand_image(input_path, scene="ecommerce")

    plan = create_upscale_plan(report, requested_mode="realistic")
    routing = build_routing_decision(plan, requested_mode="realistic")

    assert plan.candidate_types[0] == "faithful"
    assert plan.policy_version == "routing-policy-v0.10.0"
    assert "realistic" in plan.candidate_types
    assert "text" in plan.protected_regions
    assert plan.protected_region_details[0].type == "text"
    assert plan.protected_region_details[0].bbox == [0, 372, 800, 228]
    assert plan.protected_region_details[0].policy == "preserve"
    assert plan.protected_region_details[0].source == "layout_heuristic"
    assert plan.protected_region_details[1].type == "logo"
    assert plan.protected_region_details[1].bbox == [0, 0, 200, 108]
    assert routing.candidate_types == plan.candidate_types
    assert routing.policy_version == "routing-policy-v0.10.0"
    assert "protected_risk_regions" in routing.reasons


def test_product_faithful_plan_uses_only_faithful_model_without_removed_fallbacks(tmp_path):
    input_path = tmp_path / "product.png"
    Image.new("RGB", (800, 600), color=(180, 180, 185)).save(input_path)
    report = understand_image(input_path, scene="product")

    plan = create_upscale_plan(report, requested_mode="faithful")

    assert plan.candidate_types == ["faithful"]
    assert "sharpened" not in get_model_capability_registry()
    assert "material_guard" not in get_model_capability_registry()


def test_both_mode_plans_optional_multimodel_comparison_candidates(tmp_path):
    input_path = tmp_path / "product.png"
    Image.new("RGB", (800, 600), color=(180, 180, 185)).save(input_path)
    report = understand_image(input_path, scene="product")

    plan = create_upscale_plan(report, requested_mode="both")

    assert plan.candidate_types == [
        "faithful",
        "realistic",
        "swinir",
        "hat",
    ]
    assert "sharpened" not in plan.candidate_types
    assert "material_guard" not in plan.candidate_types


def test_selected_candidates_override_mode_candidate_expansion(tmp_path):
    input_path = tmp_path / "product.png"
    Image.new("RGB", (800, 600), color=(180, 180, 185)).save(input_path)
    report = understand_image(input_path, scene="product")

    plan = create_upscale_plan(report, requested_mode="both", selected_candidates=["hat", "faithful"])

    assert plan.candidate_types == ["faithful", "hat"]


def test_model_capability_registry_explains_candidate_tradeoffs():
    registry = get_model_capability_registry()

    assert registry["faithful"].hallucination_risk == "low"
    assert "preserve_product_structure" in registry["faithful"].strengths
    assert registry["realistic"].requires_manual_review is True
    assert "photo_realistic_detail_recovery" in registry["realistic"].strengths
    assert registry["swinir"].requires_manual_review is True
    assert registry["hat"].requires_manual_review is True


def test_missing_image_keeps_protection_regions_without_fake_coordinates(tmp_path):
    report = understand_image(tmp_path / "missing.png", scene="marketing")

    plan = create_upscale_plan(report, requested_mode="realistic")

    assert plan.protected_region_details[0].bbox is None
    assert plan.protected_region_details[0].source == "scene_rule"


def test_detected_regions_override_layout_heuristic_boxes(tmp_path):
    input_path = tmp_path / "poster.png"
    image = Image.new("RGB", (800, 600), color=(245, 245, 245))
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 36, 180, 92), fill=(10, 10, 10))
    draw.rectangle((120, 430, 700, 478), fill=(20, 20, 20))
    image.save(input_path)

    report = understand_image(input_path, scene="marketing")
    plan = create_upscale_plan(report, requested_mode="realistic")

    assert plan.protected_region_details[0].type == "logo"
    assert plan.protected_region_details[0].bbox == [40, 36, 141, 57]
    assert plan.protected_region_details[0].source == "vision_detector"
    assert plan.protected_region_details[1].type == "text"
    assert plan.protected_region_details[1].bbox == [120, 430, 581, 49]
    assert "vision_regions_detected" in plan.warnings


def test_detector_results_merge_with_layout_fallback_for_missing_region_types(tmp_path):
    input_path = tmp_path / "poster.png"
    image = Image.new("RGB", (800, 600), color=(245, 245, 245))
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 36, 180, 92), fill=(10, 10, 10))
    image.save(input_path)

    report = understand_image(input_path, scene="marketing")
    plan = create_upscale_plan(report, requested_mode="realistic")

    assert [region.type for region in plan.protected_region_details] == ["logo", "text"]
    assert plan.protected_region_details[0].source == "vision_detector"
    assert plan.protected_region_details[1].source == "layout_heuristic"
    assert plan.protected_region_details[1].bbox == [0, 330, 800, 270]


def test_understanding_uses_external_ocr_detector_from_settings(tmp_path, monkeypatch):
    from app.config import get_settings

    input_path = tmp_path / "poster.png"
    Image.new("RGB", (800, 600), color=(245, 245, 245)).save(input_path)
    detector = tmp_path / "ocr_detector.py"
    detector.write_text(
        "\n".join(
            [
                "import json",
                "print(json.dumps({'regions': [",
                "  {'type': 'text', 'bbox': [12, 34, 120, 28], 'confidence': 0.91, 'source': 'ocr', 'policy': 'preserve'}",
                "]}))",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("UPSCALE_REGION_DETECTOR_BACKEND", "external")
    monkeypatch.setenv("UPSCALE_REGION_DETECTOR_COMMAND", f'"{sys.executable}" "{detector}"')
    get_settings.cache_clear()

    try:
        report = understand_image(input_path, scene="marketing")
    finally:
        get_settings.cache_clear()

    assert report.detected_regions[0].source == "ocr"
    assert report.detected_regions[0].bbox == [12, 34, 120, 28]


def test_understanding_uses_tesseract_detector_from_settings(tmp_path, monkeypatch):
    from app.config import get_settings

    input_path = tmp_path / "poster.png"
    Image.new("RGB", (800, 600), color=(245, 245, 245)).save(input_path)
    detector = tmp_path / "fake_tesseract.py"
    detector.write_text(
        "\n".join(
            [
                "print('level\\tpage_num\\tblock_num\\tpar_num\\tline_num\\tword_num\\tleft\\ttop\\twidth\\theight\\tconf\\ttext')",
                "print('5\\t1\\t1\\t1\\t1\\t1\\t24\\t50\\t88\\t22\\t92\\tLOGO')",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("UPSCALE_REGION_DETECTOR_BACKEND", "tesseract")
    monkeypatch.setenv("UPSCALE_TESSERACT_COMMAND", f'"{sys.executable}" "{detector}"')
    get_settings.cache_clear()

    try:
        report = understand_image(input_path, scene="marketing")
    finally:
        get_settings.cache_clear()

    assert report.detected_regions[0].source == "tesseract_ocr"
    assert report.detected_regions[0].bbox == [24, 50, 88, 22]


def test_understanding_uses_external_logo_detector_from_settings(tmp_path, monkeypatch):
    from app.config import get_settings

    input_path = tmp_path / "poster.png"
    Image.new("RGB", (800, 600), color=(245, 245, 245)).save(input_path)
    logo_detector = tmp_path / "logo_detector.py"
    logo_detector.write_text(
        "\n".join(
            [
                "import json",
                "print(json.dumps({'regions': [",
                "  {'type': 'logo', 'bbox': [40, 24, 96, 52], 'confidence': 0.82}",
                "]}))",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("UPSCALE_LOGO_DETECTOR_BACKEND", "external")
    monkeypatch.setenv("UPSCALE_LOGO_DETECTOR_COMMAND", f'"{sys.executable}" "{logo_detector}"')
    get_settings.cache_clear()

    try:
        report = understand_image(input_path, scene="marketing")
    finally:
        get_settings.cache_clear()

    assert report.detected_regions[0].type == "logo"
    assert report.detected_regions[0].source == "logo_detector"
    assert report.detected_regions[0].bbox == [40, 24, 96, 52]
