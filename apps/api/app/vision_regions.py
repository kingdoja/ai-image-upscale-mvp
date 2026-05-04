from pathlib import Path
import csv
import json
import tempfile
import subprocess
from io import StringIO
from typing import List, Optional, Sequence, Union

from PIL import Image
from pydantic import BaseModel


class VisionRegion(BaseModel):
    type: str
    bbox: List[int]
    confidence: float
    source: str = "vision_detector"
    policy: str = "preserve"


Command = Union[str, Sequence[str]]


def _bounding_box(points: List[tuple]) -> Optional[List[int]]:
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    return [min_x, min_y, max_x - min_x + 1, max_y - min_y + 1]


def _dark_points(image: Image.Image, *, x_min: int, x_max: int, y_min: int, y_max: int) -> List[tuple]:
    pixels = image.load()
    points = []
    width, height = image.size
    x_max = min(x_max, width)
    y_max = min(y_max, height)
    for y in range(max(0, y_min), y_max):
        for x in range(max(0, x_min), x_max):
            r, g, b = pixels[x, y][:3]
            if (r + g + b) / 3 < 64:
                points.append((x, y))
    return points


def _region_from_window(image: Image.Image, region_type: str, window: tuple) -> Optional[VisionRegion]:
    points = _dark_points(
        image,
        x_min=window[0],
        y_min=window[1],
        x_max=window[2],
        y_max=window[3],
    )
    bbox = _bounding_box(points)
    if not bbox:
        return None
    area = bbox[2] * bbox[3]
    if area < 24:
        return None
    window_area = max(1, (window[2] - window[0]) * (window[3] - window[1]))
    if area / window_area > 0.75:
        return None
    if region_type == "logo" and bbox[3] > 0 and bbox[2] / bbox[3] > 3.0:
        return None
    return VisionRegion(
        type=region_type,
        bbox=bbox,
        confidence=0.8,
    )


def _colored_badge_points(image: Image.Image) -> List[tuple]:
    pixels = image.load()
    points = []
    width, height = image.size
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y][:3]
            max_channel = max(r, g, b)
            min_channel = min(r, g, b)
            saturation = max_channel - min_channel
            brightness = (r + g + b) / 3
            if saturation > 90 and 45 < brightness < 245:
                points.append((x, y))
    return points


def _colored_badge_region(image: Image.Image) -> Optional[VisionRegion]:
    points = _colored_badge_points(image)
    bbox = _bounding_box(points)
    if not bbox:
        return None
    width, height = image.size
    image_area = max(1, width * height)
    area = bbox[2] * bbox[3]
    point_ratio = len(points) / image_area
    bbox_ratio = area / image_area
    if point_ratio < 0.03 or bbox_ratio > 0.55:
        return None
    if bbox[2] < width * 0.12 or bbox[3] < height * 0.12:
        return None
    return VisionRegion(
        type="logo",
        bbox=bbox,
        confidence=0.72,
        source="graphic_mark_detector",
    )


def _local_detect_protected_regions(input_path: Path, *, scene: str) -> List[VisionRegion]:
    if scene not in {"marketing", "ecommerce"} or not input_path.exists():
        return []

    with Image.open(input_path) as raw_image:
        image = raw_image.convert("RGB")
        width, height = image.size
        windows = [
            ("logo", (0, 0, round(width * 0.35), round(height * 0.25))),
            ("text", (0, round(height * 0.45), width, height)),
        ]
        regions = [
            region
            for region_type, window in windows
            for region in [_region_from_window(image, region_type, window)]
            if region is not None
        ]
        if not any(region.type == "logo" for region in regions):
            colored_badge = _colored_badge_region(image)
            if colored_badge is not None:
                regions.insert(0, colored_badge)
    return regions


def _parse_external_regions(
    stdout: str,
    *,
    allowed_types: Optional[set] = None,
    default_source: str = "external_detector",
) -> List[VisionRegion]:
    loaded = json.loads(stdout)
    rows = loaded.get("regions", loaded) if isinstance(loaded, dict) else loaded
    if not isinstance(rows, list):
        return []
    allowed_types = allowed_types or {"text", "logo"}
    regions = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        bbox = row.get("bbox")
        region_type = row.get("type")
        if region_type not in allowed_types:
            continue
        if not isinstance(bbox, list) or len(bbox) != 4:
            continue
        try:
            regions.append(
                VisionRegion(
                    type=region_type,
                    bbox=[int(value) for value in bbox],
                    confidence=float(row.get("confidence", 0.75)),
                    source=str(row.get("source", default_source)),
                    policy=str(row.get("policy", "preserve")),
                )
            )
        except (TypeError, ValueError):
            continue
    return regions


def _format_command(command: str, input_path: Path, scene: str) -> str:
    if "{input}" in command or "{scene}" in command:
        return command.replace("{input}", str(input_path)).replace("{scene}", scene)
    return f'{command} "{input_path}" "{scene}"'


def _run_external_detector(
    input_path: Path,
    *,
    scene: str,
    external_command: Command,
    timeout_seconds: int,
    allowed_types: Optional[set] = None,
    default_source: str = "external_detector",
) -> List[VisionRegion]:
    if not external_command:
        return []
    if isinstance(external_command, str):
        try:
            completed = subprocess.run(
                _format_command(external_command, input_path, scene),
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
            )
        except (OSError, subprocess.SubprocessError):
            return []
    else:
        try:
            completed = subprocess.run(
                [*external_command, str(input_path), scene],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
            )
        except (OSError, subprocess.SubprocessError):
            return []
    if completed.returncode != 0:
        return []
    try:
        return _parse_external_regions(
            completed.stdout,
            allowed_types=allowed_types,
            default_source=default_source,
        )
    except (json.JSONDecodeError, ValueError, TypeError):
        return []


def _run_logo_detector(
    input_path: Path,
    *,
    scene: str,
    logo_detector_backend: str,
    logo_detector_command: Command,
    timeout_seconds: int,
) -> List[VisionRegion]:
    if logo_detector_backend != "external":
        return []
    return _run_external_detector(
        input_path,
        scene=scene,
        external_command=logo_detector_command,
        timeout_seconds=timeout_seconds,
        allowed_types={"logo"},
        default_source="logo_detector",
    )


def _parse_tesseract_tsv(stdout: str) -> List[VisionRegion]:
    reader = csv.DictReader(StringIO(stdout), delimiter="\t")
    boxes = []
    confidences = []
    for row in reader:
        text = (row.get("text") or "").strip()
        if not text:
            continue
        try:
            confidence = float(row.get("conf", -1))
            left = int(float(row.get("left", 0)))
            top = int(float(row.get("top", 0)))
            width = int(float(row.get("width", 0)))
            height = int(float(row.get("height", 0)))
        except (TypeError, ValueError):
            continue
        if confidence < 0 or width <= 0 or height <= 0:
            continue
        boxes.append((left, top, left + width, top + height))
        confidences.append(confidence)
    if not boxes:
        return []
    x1 = min(box[0] for box in boxes)
    y1 = min(box[1] for box in boxes)
    x2 = max(box[2] for box in boxes)
    y2 = max(box[3] for box in boxes)
    return [
        VisionRegion(
            type="text",
            bbox=[x1, y1, x2 - x1, y2 - y1],
            confidence=round((sum(confidences) / len(confidences)) / 100, 3),
            source="tesseract_ocr",
            policy="preserve",
        )
    ]


def _shift_region(region: VisionRegion, *, left: int, top: int) -> VisionRegion:
    return VisionRegion(
        type=region.type,
        bbox=[region.bbox[0] + left, region.bbox[1] + top, region.bbox[2], region.bbox[3]],
        confidence=region.confidence,
        source=region.source,
        policy=region.policy,
    )


def _scale_region(region: VisionRegion, *, divisor: int) -> VisionRegion:
    return VisionRegion(
        type=region.type,
        bbox=[
            round(region.bbox[0] / divisor),
            round(region.bbox[1] / divisor),
            max(1, round(region.bbox[2] / divisor)),
            max(1, round(region.bbox[3] / divisor)),
        ],
        confidence=region.confidence,
        source=region.source,
        policy=region.policy,
    )


def _score_text_region(region: VisionRegion, *, image_width: int, image_height: int) -> float:
    bbox = region.bbox
    area = max(1, bbox[2] * bbox[3])
    image_area = max(1, image_width * image_height)
    area_ratio = min(1.0, area / image_area)
    center_y = bbox[1] + bbox[3] / 2
    y_ratio = min(1.0, max(0.0, center_y / max(1, image_height)))
    confidence = max(0.0, min(1.0, region.confidence))
    return confidence * area_ratio * max(0.1, 1.0 - area_ratio) * max(0.1, 1.0 - y_ratio)


def _badge_text_fallback_regions(
    *,
    logo_regions: List[VisionRegion],
    image_width: int,
    image_height: int,
) -> List[VisionRegion]:
    fallback_regions = []
    image_area = max(1, image_width * image_height)
    for region in logo_regions:
        if region.source != "graphic_mark_detector":
            continue
        area_ratio = (region.bbox[2] * region.bbox[3]) / image_area
        if area_ratio < 0.08 or area_ratio > 0.75:
            continue
        fallback_regions.append(
            VisionRegion(
                type="text",
                bbox=region.bbox,
                confidence=min(region.confidence, 0.58),
                source="badge_text_fallback",
                policy="manual_review",
            )
        )
    return fallback_regions


def _guided_text_crop_boxes(image: Image.Image, *, logo_regions: List[VisionRegion]) -> List[tuple]:
    width, height = image.size
    boxes = []
    if logo_regions:
        logo = max(logo_regions, key=lambda region: region.bbox[2] * region.bbox[3]).bbox
        x, y, box_width, box_height = logo
        square_size = min(
            width,
            height,
            max(
                round(box_width * 1.4),
                round(box_height * 1.7),
                round(width * 0.42),
                round(height * 0.42),
            ),
        )
        if square_size >= 120:
            boxes.append((0, 0, square_size, square_size))
        left = max(0, x - round(box_width * 0.15))
        top = max(0, y - round(box_height * 0.2))
        right = min(width, x + box_width + round(box_width * 0.4))
        bottom = min(height, y + box_height + round(box_height * 0.8))
        if right - left >= 120 and bottom - top >= 120:
            boxes.append((left, top, right, bottom))
    else:
        upper = (0, 0, width, max(1, round(height * 0.8)))
        if upper[2] - upper[0] >= 120 and upper[3] - upper[1] >= 120:
            boxes.append(upper)
    return boxes


def _run_tesseract_detector_on_image(
    image_path: Path,
    *,
    tesseract_command: Command,
    timeout_seconds: int,
    psm: int,
) -> List[VisionRegion]:
    if not tesseract_command or not image_path.exists():
        return []
    if isinstance(tesseract_command, str):
        command = _format_tesseract_command_psm(tesseract_command, image_path, psm)
        try:
            completed = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
            )
        except (OSError, subprocess.SubprocessError):
            return []
    else:
        try:
            completed = subprocess.run(
                [*tesseract_command, str(image_path), "stdout", "--psm", str(psm), "tsv"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
            )
        except (OSError, subprocess.SubprocessError):
            return []
    if completed.returncode != 0:
        return []
    return _parse_tesseract_tsv(completed.stdout)


def _format_tesseract_command(command: str, input_path: Path) -> str:
    if "{input}" in command:
        return command.replace("{input}", str(input_path))
    return f'{command} "{input_path}" stdout --psm 6 tsv'


def _format_tesseract_command_psm(command: str, input_path: Path, psm: int) -> str:
    if "{input}" in command:
        return command.replace("{input}", str(input_path))
    return f'{command} "{input_path}" stdout --psm {psm} tsv'


def _guided_text_crop(image: Image.Image, *, logo_regions: List[VisionRegion]) -> Optional[Image.Image]:
    width, height = image.size
    if width < 80 or height < 80:
        return None
    if logo_regions:
        logo = max(logo_regions, key=lambda region: region.bbox[2] * region.bbox[3]).bbox
        x1, y1, box_width, box_height = logo
        left = max(0, x1 - round(box_width * 0.5))
        top = max(0, y1 - round(box_height * 0.7))
        right = min(width, x1 + box_width + round(box_width * 1.2))
        bottom = min(height, y1 + box_height + round(box_height * 2.0))
        if right - left >= 120 and bottom - top >= 120:
            return image.crop((left, top, right, bottom))
    upper = image.crop((0, 0, width, max(1, round(height * 0.8))))
    return upper if upper.size[0] >= 120 and upper.size[1] >= 120 else None


def _run_tesseract_detector(
    input_path: Path,
    *,
    tesseract_command: Command,
    timeout_seconds: int,
    logo_regions: Optional[List[VisionRegion]] = None,
) -> List[VisionRegion]:
    if not tesseract_command or not input_path.exists():
        return []
    if logo_regions is None:
        logo_regions = []
    primary_regions = _run_tesseract_detector_on_image(
        input_path,
        tesseract_command=tesseract_command,
        timeout_seconds=timeout_seconds,
        psm=6,
    )
    with Image.open(input_path) as raw_image:
        image = raw_image.convert("RGB")
        guided_candidates = []
        for index, crop_box in enumerate(_guided_text_crop_boxes(image, logo_regions=logo_regions)):
            with tempfile.NamedTemporaryFile(prefix=f"{input_path.stem}-guide-{index}-", suffix=".png", delete=False) as handle:
                crop_path = Path(handle.name)
            try:
                crop_image = image.crop(crop_box)
                crop_image = crop_image.resize((crop_image.width * 2, crop_image.height * 2))
                crop_image.save(crop_path)
                guided_regions = _run_tesseract_detector_on_image(
                    crop_path,
                    tesseract_command=tesseract_command,
                    timeout_seconds=timeout_seconds,
                    psm=11,
                )
            finally:
                try:
                    crop_path.unlink()
                except OSError:
                    pass
            if not guided_regions:
                continue
            guided_candidate = _shift_region(
                _scale_region(guided_regions[0], divisor=2),
                left=crop_box[0],
                top=crop_box[1],
            )
            guided_candidates.append(guided_candidate)

    text_candidates = [region for region in primary_regions if region.type == "text"]
    text_candidates.extend(guided_candidates)
    if not text_candidates:
        with Image.open(input_path) as raw_image:
            image_width, image_height = raw_image.size
        text_candidates.extend(
            _badge_text_fallback_regions(
                logo_regions=logo_regions,
                image_width=image_width,
                image_height=image_height,
            )
        )
    if not text_candidates:
        return []

    if len(text_candidates) == 1:
        return text_candidates

    image_width, image_height = input_path.stat().st_size, input_path.stat().st_size
    with Image.open(input_path) as raw_image:
        image_width, image_height = raw_image.size
    selected = max(
        text_candidates,
        key=lambda region: _score_text_region(region, image_width=image_width, image_height=image_height),
    )
    return [selected]


def _merge_regions_by_type(*region_groups: List[VisionRegion]) -> List[VisionRegion]:
    merged = []
    index_by_type = {}
    for regions in region_groups:
        for region in regions:
            existing_index = index_by_type.get(region.type)
            if existing_index is None:
                index_by_type[region.type] = len(merged)
                merged.append(region)
                continue
            existing = merged[existing_index]
            if existing.type == "text" and existing.source == "tesseract_ocr":
                continue
            if region.confidence > existing.confidence:
                merged[existing_index] = region
    return merged


def detect_protected_regions(
    input_path: Path,
    *,
    scene: str,
    backend: str = "local",
    external_command: Command = "",
    tesseract_command: Command = "tesseract",
    logo_detector_backend: str = "local",
    logo_detector_command: Command = "",
    timeout_seconds: int = 30,
) -> List[VisionRegion]:
    if scene not in {"marketing", "ecommerce"} or not input_path.exists():
        return []
    logo_regions = _run_logo_detector(
        input_path,
        scene=scene,
        logo_detector_backend=logo_detector_backend,
        logo_detector_command=logo_detector_command,
        timeout_seconds=timeout_seconds,
    )
    local_regions = _local_detect_protected_regions(input_path, scene=scene)
    if backend == "external":
        external_regions = _run_external_detector(
            input_path,
            scene=scene,
            external_command=external_command,
            timeout_seconds=timeout_seconds,
        )
        if external_regions:
            return _merge_regions_by_type(external_regions, logo_regions, local_regions)
    if backend == "tesseract":
        tesseract_regions = _run_tesseract_detector(
            input_path,
            tesseract_command=tesseract_command,
            timeout_seconds=timeout_seconds,
            logo_regions=[
                region
                for region in [*logo_regions, *local_regions]
                if region.type == "logo"
            ],
        )
        if tesseract_regions:
            return _merge_regions_by_type(
                tesseract_regions,
                logo_regions,
                local_regions,
            )
    return _merge_regions_by_type(logo_regions, local_regions)
