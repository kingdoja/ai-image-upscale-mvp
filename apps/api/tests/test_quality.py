from PIL import Image

from app.quality import evaluate_image


def test_quality_low_risk_for_normal_image(tmp_path):
    input_path = tmp_path / "input.png"
    result_path = tmp_path / "result.png"
    Image.new("RGB", (16, 16)).save(input_path)
    Image.new("RGB", (64, 64)).save(result_path)

    quality = evaluate_image(input_path, result_path)

    assert quality.risk_level == "low"
    assert quality.quality_score == 0.8
    assert quality.breakdown.clarity == 0.8
    assert quality.breakdown.hallucination_risk == 0.1


def test_quality_medium_risk_for_text_or_logo(tmp_path):
    input_path = tmp_path / "input.png"
    result_path = tmp_path / "result.png"
    Image.new("RGB", (16, 16)).save(input_path)
    Image.new("RGB", (64, 64)).save(result_path)

    quality = evaluate_image(input_path, result_path, contains_text=True, contains_logo=True)

    assert quality.risk_level == "medium"
    assert quality.quality_score == 0.6
    assert "text_region_requires_review" in quality.warnings
    assert quality.breakdown.logo_text == 0.5
    assert quality.breakdown.hallucination_risk == 0.4


def test_quality_high_risk_for_missing_result(tmp_path):
    input_path = tmp_path / "input.png"
    Image.new("RGB", (16, 16)).save(input_path)

    quality = evaluate_image(input_path, tmp_path / "missing.png")

    assert quality.risk_level == "high"
    assert quality.quality_score == 0.4
    assert quality.breakdown.structure == 0.4


def test_quality_high_risk_for_structure_warning(tmp_path):
    input_path = tmp_path / "input.png"
    result_path = tmp_path / "result.png"
    Image.new("RGB", (16, 16)).save(input_path)
    Image.new("RGB", (64, 64)).save(result_path)

    quality = evaluate_image(input_path, result_path, structural_risk=True)

    assert quality.risk_level == "high"
    assert quality.quality_score == 0.4
    assert "structure_region_requires_review" in quality.warnings
    assert quality.breakdown.structure == 0.4
