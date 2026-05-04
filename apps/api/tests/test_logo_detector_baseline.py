from pathlib import Path
import sys

from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


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


def test_baseline_logo_detector_finds_center_graphic_mark(tmp_path):
    from tools.logo_detector_baseline import detect_logo_regions

    image_path = tmp_path / "label.png"
    image = Image.new("RGB", (800, 600), color=(130, 70, 20))
    draw = ImageDraw.Draw(image)
    draw.ellipse((300, 180, 500, 380), fill=(245, 245, 240))
    draw.polygon([(390, 250), (430, 250), (410, 330)], fill=(240, 210, 20))
    draw.rectangle((330, 260, 365, 290), fill=(20, 20, 20))
    draw.rectangle((455, 260, 490, 290), fill=(20, 20, 20))
    image.save(image_path)

    regions = detect_logo_regions(image_path, scene="marketing")

    assert len(regions) == 1
    assert regions[0]["type"] == "logo"
    assert regions[0]["source"] == "logo_detector_baseline"
    assert regions[0]["bbox"][0] <= 300
    assert regions[0]["bbox"][1] <= 180
    assert regions[0]["bbox"][2] >= 190
    assert regions[0]["bbox"][3] >= 190


def test_baseline_logo_detector_ignores_plain_product_image(tmp_path):
    from tools.logo_detector_baseline import detect_logo_regions

    image_path = tmp_path / "plain.png"
    Image.new("RGB", (800, 600), color=(245, 245, 245)).save(image_path)

    regions = detect_logo_regions(image_path, scene="product")

    assert regions == []


def test_baseline_logo_detector_ignores_text_only_marketing_layout(tmp_path):
    from tools.logo_detector_baseline import detect_logo_regions

    image_path = tmp_path / "text-only.png"
    image = Image.new("RGB", (800, 600), color=(246, 241, 232))
    draw = ImageDraw.Draw(image)
    for top, width in [(185, 330), (230, 295), (275, 250), (320, 310)]:
        draw.rectangle((245, top, 245 + width, top + 22), fill=(25, 35, 45))
    image.save(image_path)

    regions = detect_logo_regions(image_path, scene="marketing")

    assert regions == []


def test_baseline_logo_detector_prefers_compact_mark_over_adjacent_packaging_noise(tmp_path):
    from tools.logo_detector_baseline import detect_logo_regions

    image_path = tmp_path / "packaging-noise.png"
    image = Image.new("RGB", (800, 533), color=(64, 140, 69))
    draw = ImageDraw.Draw(image)
    draw.rectangle((224, 133, 315, 384), fill=(15, 25, 20))
    draw.rectangle((326, 231, 516, 384), fill=(248, 248, 242))
    draw.rectangle((420, 285, 570, 360), fill=(18, 28, 36))
    draw.rectangle((440, 304, 550, 340), fill=(245, 245, 240))
    image.save(image_path)

    regions = detect_logo_regions(image_path, scene="ecommerce")

    assert len(regions) == 1
    assert regions[0]["bbox"][0] >= 326
    assert regions[0]["bbox"][2] <= 260
    assert regions[0]["bbox"][3] <= 170


def test_baseline_logo_detector_localizes_commons_packaging_logo():
    from tools.logo_detector_baseline import detect_logo_regions

    image_path = PROJECT_ROOT / "datasets" / "region-eval" / "samples" / "commons-produk-packaging.jpg"

    regions = detect_logo_regions(image_path, scene="ecommerce")

    assert len(regions) == 1
    assert _bbox_iou([420, 285, 150, 75], regions[0]["bbox"]) >= 0.3
