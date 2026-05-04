from pathlib import Path
import json
import sys

from PIL import Image, ImageDraw
import pytest

from app.vision_regions import detect_protected_regions


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _bbox_iou(first, second):
    first_x1, first_y1, first_w, first_h = first
    second_x1, second_y1, second_w, second_h = second
    first_x2 = first_x1 + first_w
    first_y2 = first_y1 + first_h
    second_x2 = second_x1 + second_w
    second_y2 = second_y1 + second_h
    intersection_w = max(0, min(first_x2, second_x2) - max(first_x1, second_x1))
    intersection_h = max(0, min(first_y2, second_y2) - max(first_y1, second_y1))
    intersection = intersection_w * intersection_h
    union = first_w * first_h + second_w * second_h - intersection
    return 0.0 if union <= 0 else intersection / union


def test_detect_protected_regions_finds_dark_logo_and_text_blocks(tmp_path):
    image_path = tmp_path / "poster.png"
    image = Image.new("RGB", (800, 600), color=(245, 245, 245))
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 36, 180, 92), fill=(10, 10, 10))
    draw.rectangle((120, 430, 700, 478), fill=(20, 20, 20))
    image.save(image_path)

    regions = detect_protected_regions(image_path, scene="marketing")

    assert [region.type for region in regions] == ["logo", "text"]
    assert regions[0].bbox == [40, 36, 141, 57]
    assert regions[0].source == "vision_detector"
    assert regions[1].bbox == [120, 430, 581, 49]
    assert regions[1].confidence >= 0.75


def test_detect_protected_regions_returns_empty_for_plain_image(tmp_path):
    image_path = tmp_path / "plain.png"
    Image.new("RGB", (800, 600), color=(245, 245, 245)).save(image_path)

    regions = detect_protected_regions(image_path, scene="marketing")

    assert regions == []


def test_detect_protected_regions_does_not_treat_wide_title_text_as_logo(tmp_path):
    image_path = tmp_path / "title-text.png"
    image = Image.new("RGB", (800, 600), color=(246, 241, 232))
    draw = ImageDraw.Draw(image)
    draw.rectangle((85, 88, 365, 116), fill=(20, 30, 40))
    draw.rectangle((88, 132, 330, 156), fill=(20, 30, 40))
    image.save(image_path)

    regions = detect_protected_regions(image_path, scene="marketing")

    assert not any(region.type == "logo" for region in regions)


def test_detect_protected_regions_finds_colored_badge_logo(tmp_path):
    image_path = tmp_path / "badge.png"
    image = Image.new("RGB", (800, 600), color=(250, 250, 250))
    draw = ImageDraw.Draw(image)
    draw.ellipse((260, 80, 540, 360), fill=(230, 20, 30))
    draw.text((340, 205), "NEW", fill=(255, 255, 255))
    image.save(image_path)

    regions = detect_protected_regions(image_path, scene="marketing")

    assert regions[0].type == "logo"
    assert regions[0].source == "graphic_mark_detector"
    assert regions[0].bbox[0] <= 270
    assert regions[0].bbox[1] <= 90
    assert regions[0].bbox[2] >= 260
    assert regions[0].bbox[3] >= 260


def test_detect_protected_regions_ignores_full_dark_background(tmp_path):
    image_path = tmp_path / "dark.png"
    Image.new("RGB", (800, 600), color=(20, 20, 20)).save(image_path)

    regions = detect_protected_regions(image_path, scene="marketing")

    assert regions == []


def test_external_region_detector_reads_json_regions_from_command(tmp_path):
    image_path = tmp_path / "poster.png"
    Image.new("RGB", (800, 600), color=(245, 245, 245)).save(image_path)
    detector = tmp_path / "detector.py"
    detector.write_text(
        "\n".join(
            [
                "import json",
                "import sys",
                "payload = {'regions': [",
                "  {'type': 'text', 'bbox': [12, 34, 120, 28], 'confidence': 0.91, 'source': 'ocr', 'policy': 'preserve'},",
                "  {'type': 'logo', 'bbox': [40, 20, 80, 35], 'confidence': 0.88, 'source': 'logo_detector', 'policy': 'preserve'},",
                "]}",
                "print(json.dumps(payload))",
            ]
        ),
        encoding="utf-8",
    )

    regions = detect_protected_regions(
        image_path,
        scene="marketing",
        backend="external",
        external_command=[sys.executable, str(detector)],
    )

    assert [region.type for region in regions] == ["text", "logo"]
    assert regions[0].bbox == [12, 34, 120, 28]
    assert regions[0].source == "ocr"
    assert regions[1].source == "logo_detector"


def test_external_region_detector_falls_back_to_local_when_command_fails(tmp_path):
    image_path = tmp_path / "poster.png"
    image = Image.new("RGB", (800, 600), color=(245, 245, 245))
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 36, 180, 92), fill=(10, 10, 10))
    image.save(image_path)

    regions = detect_protected_regions(
        image_path,
        scene="marketing",
        backend="external",
        external_command=[sys.executable, str(tmp_path / "missing.py")],
    )

    assert regions[0].source == "vision_detector"
    assert regions[0].bbox == [40, 36, 141, 57]


def test_tesseract_region_detector_reads_tsv_word_boxes(tmp_path):
    image_path = tmp_path / "poster.png"
    Image.new("RGB", (800, 600), color=(245, 245, 245)).save(image_path)
    detector = tmp_path / "fake_tesseract.py"
    detector.write_text(
        "\n".join(
            [
                "print('level\\tpage_num\\tblock_num\\tpar_num\\tline_num\\tword_num\\tleft\\ttop\\twidth\\theight\\tconf\\ttext')",
                "print('5\\t1\\t1\\t1\\t1\\t1\\t12\\t34\\t40\\t20\\t91\\tSALE')",
                "print('5\\t1\\t1\\t1\\t1\\t2\\t60\\t36\\t72\\t18\\t88\\tNOW')",
                "print('5\\t1\\t1\\t1\\t1\\t3\\t140\\t40\\t40\\t20\\t-1\\t')",
            ]
        ),
        encoding="utf-8",
    )

    regions = detect_protected_regions(
        image_path,
        scene="marketing",
        backend="tesseract",
        tesseract_command=[sys.executable, str(detector)],
    )

    assert len(regions) == 1
    assert regions[0].type == "text"
    assert regions[0].bbox == [12, 34, 120, 20]
    assert regions[0].source == "tesseract_ocr"
    assert regions[0].confidence == 0.895


def test_tesseract_region_detector_ignores_product_scene(tmp_path):
    image_path = tmp_path / "plain-product.png"
    Image.new("RGB", (800, 600), color=(245, 245, 245)).save(image_path)
    detector = tmp_path / "fake_tesseract.py"
    detector.write_text(
        "\n".join(
            [
                "print('level\\tpage_num\\tblock_num\\tpar_num\\tline_num\\tword_num\\tleft\\ttop\\twidth\\theight\\tconf\\ttext')",
                "print('5\\t1\\t1\\t1\\t1\\t1\\t120\\t240\\t180\\t30\\t88\\tNOISE')",
            ]
        ),
        encoding="utf-8",
    )

    regions = detect_protected_regions(
        image_path,
        scene="product",
        backend="tesseract",
        tesseract_command=[sys.executable, str(detector)],
    )

    assert regions == []


def test_tesseract_region_detector_keeps_local_logo_detection(tmp_path):
    image_path = tmp_path / "poster.png"
    image = Image.new("RGB", (800, 600), color=(245, 245, 245))
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 36, 180, 92), fill=(10, 10, 10))
    image.save(image_path)
    detector = tmp_path / "fake_tesseract.py"
    detector.write_text(
        "\n".join(
            [
                "print('level\\tpage_num\\tblock_num\\tpar_num\\tline_num\\tword_num\\tleft\\ttop\\twidth\\theight\\tconf\\ttext')",
                "print('5\\t1\\t1\\t1\\t1\\t1\\t12\\t340\\t88\\t22\\t92\\tSALE')",
            ]
        ),
        encoding="utf-8",
    )

    regions = detect_protected_regions(
        image_path,
        scene="marketing",
        backend="tesseract",
        tesseract_command=[sys.executable, str(detector)],
    )

    assert [region.type for region in regions] == ["text", "logo"]
    assert regions[0].source == "tesseract_ocr"
    assert regions[0].bbox == [12, 340, 88, 22]
    assert regions[1].source == "vision_detector"
    assert regions[1].bbox == [40, 36, 141, 57]


def test_tesseract_region_detector_localizes_cc0_product_label_text():
    image_path = PROJECT_ROOT / "datasets" / "region-eval" / "samples" / "cc0-product-label.jpg"
    tesseract_path = Path("D:/Tools/Tesseract-OCR/tesseract.exe")
    if not tesseract_path.exists():
        pytest.skip("local Tesseract install is not available")

    regions = detect_protected_regions(
        image_path,
        scene="marketing",
        backend="tesseract",
        tesseract_command=f'"{tesseract_path}"',
        logo_detector_backend="external",
        logo_detector_command=f'"{sys.executable}" "{PROJECT_ROOT / "tools" / "logo_detector_baseline.py"}"',
    )

    text_regions = [region for region in regions if region.type == "text"]
    assert text_regions
    assert _bbox_iou([100, 80, 1045, 1370], text_regions[0].bbox) >= 0.3


def test_tesseract_region_detector_localizes_cc0_new_label_badge_text():
    image_path = PROJECT_ROOT / "datasets" / "region-eval" / "samples" / "cc0-new-label.jpg"
    tesseract_path = Path("D:/Tools/Tesseract-OCR/tesseract.exe")
    if not tesseract_path.exists():
        pytest.skip("local Tesseract install is not available")

    regions = detect_protected_regions(
        image_path,
        scene="marketing",
        backend="tesseract",
        tesseract_command=f'"{tesseract_path}"',
        logo_detector_backend="external",
        logo_detector_command=f'"{sys.executable}" "{PROJECT_ROOT / "tools" / "logo_detector_baseline.py"}"',
    )

    text_regions = [region for region in regions if region.type == "text"]
    assert text_regions
    assert _bbox_iou([512, 385, 850, 510], text_regions[0].bbox) >= 0.3


def test_tesseract_region_detector_retries_on_guided_crop_when_primary_pass_misses_text(tmp_path):
    image_path = tmp_path / "poster.png"
    image = Image.new("RGB", (800, 600), color=(245, 245, 245))
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 36, 180, 92), fill=(10, 10, 10))
    draw.rectangle((120, 430, 700, 478), fill=(20, 20, 20))
    image.save(image_path)

    calls_log = tmp_path / "calls.txt"
    detector = tmp_path / "fake_tesseract.py"
    detector.write_text(
        "\n".join(
            [
                "import pathlib",
                "import sys",
                f'calls_log = pathlib.Path(r"{calls_log}")',
                "calls_log.write_text(calls_log.read_text(encoding='utf-8') + '\\n'.join(sys.argv) + '\\n', encoding='utf-8') if calls_log.exists() else calls_log.write_text('\\n'.join(sys.argv) + '\\n', encoding='utf-8')",
                "image_arg = sys.argv[1] if len(sys.argv) > 1 else ''",
                "if 'guide' in pathlib.Path(image_arg).name:",
                "    print('level\\tpage_num\\tblock_num\\tpar_num\\tline_num\\tword_num\\tleft\\ttop\\twidth\\theight\\tconf\\ttext')",
                "    print('5\\t1\\t1\\t1\\t1\\t1\\t212\\t584\\t1686\\t1023\\t95\\tNEW')",
                "else:",
                "    print('level\\tpage_num\\tblock_num\\tpar_num\\tline_num\\tword_num\\tleft\\ttop\\twidth\\theight\\tconf\\ttext')",
            ]
        ),
        encoding="utf-8",
    )

    regions = detect_protected_regions(
        image_path,
        scene="marketing",
        backend="tesseract",
        tesseract_command=[sys.executable, str(detector)],
    )

    calls = calls_log.read_text(encoding="utf-8")
    assert "guide" in calls
    assert any(region.type == "text" for region in regions)


def test_tesseract_region_detector_merges_external_logo_detector(tmp_path):
    image_path = tmp_path / "poster.png"
    Image.new("RGB", (800, 600), color=(245, 245, 245)).save(image_path)
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
                "  {'type': 'logo', 'bbox': [44, 36, 132, 54], 'confidence': 0.86}",
                "]}))",
            ]
        ),
        encoding="utf-8",
    )

    regions = detect_protected_regions(
        image_path,
        scene="marketing",
        backend="tesseract",
        tesseract_command=[sys.executable, str(tesseract)],
        logo_detector_backend="external",
        logo_detector_command=[sys.executable, str(logo_detector)],
    )

    assert [region.type for region in regions] == ["text", "logo"]
    assert regions[0].source == "tesseract_ocr"
    assert regions[1].bbox == [44, 36, 132, 54]
    assert regions[1].source == "logo_detector"


def test_low_confidence_external_logo_does_not_replace_stronger_local_logo(tmp_path):
    image_path = tmp_path / "poster.png"
    image = Image.new("RGB", (800, 600), color=(245, 245, 245))
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 36, 180, 92), fill=(10, 10, 10))
    image.save(image_path)
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
                "  {'type': 'logo', 'bbox': [300, 220, 180, 140], 'confidence': 0.2, 'source': 'logo_detector'}",
                "]}))",
            ]
        ),
        encoding="utf-8",
    )

    regions = detect_protected_regions(
        image_path,
        scene="marketing",
        backend="tesseract",
        tesseract_command=[sys.executable, str(tesseract)],
        logo_detector_backend="external",
        logo_detector_command=[sys.executable, str(logo_detector)],
    )

    assert [region.type for region in regions] == ["text", "logo"]
    assert regions[1].source == "vision_detector"
    assert regions[1].bbox == [40, 36, 141, 57]


def test_external_logo_detector_falls_back_to_local_logo_detection(tmp_path):
    image_path = tmp_path / "poster.png"
    image = Image.new("RGB", (800, 600), color=(245, 245, 245))
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 36, 180, 92), fill=(10, 10, 10))
    image.save(image_path)

    regions = detect_protected_regions(
        image_path,
        scene="marketing",
        logo_detector_backend="external",
        logo_detector_command=[sys.executable, str(tmp_path / "missing_logo_detector.py")],
    )

    assert regions[0].type == "logo"
    assert regions[0].source == "vision_detector"
    assert regions[0].bbox == [40, 36, 141, 57]


def test_tesseract_region_detector_falls_back_to_local_when_command_fails(tmp_path):
    image_path = tmp_path / "poster.png"
    image = Image.new("RGB", (800, 600), color=(245, 245, 245))
    draw = ImageDraw.Draw(image)
    draw.rectangle((120, 430, 700, 478), fill=(20, 20, 20))
    image.save(image_path)

    regions = detect_protected_regions(
        image_path,
        scene="marketing",
        backend="tesseract",
        tesseract_command=[sys.executable, str(tmp_path / "missing_tesseract.py")],
    )

    assert regions[0].source == "vision_detector"
    assert regions[0].type == "text"
