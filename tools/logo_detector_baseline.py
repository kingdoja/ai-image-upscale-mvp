from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys
from typing import Dict, List, Optional, Tuple

from PIL import Image


Region = Dict[str, object]


def _bounding_box(points: List[Tuple[int, int]]) -> Optional[List[int]]:
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return [min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1]


def _is_graphic_mark_pixel(red: int, green: int, blue: int) -> bool:
    max_channel = max(red, green, blue)
    min_channel = min(red, green, blue)
    brightness = (red + green + blue) / 3
    saturation = max_channel - min_channel
    return brightness > 210 or brightness < 65 or saturation > 105


def _color_distance(first: Tuple[int, int, int], second: Tuple[int, int, int]) -> float:
    return sum((first[index] - second[index]) ** 2 for index in range(3)) ** 0.5


def _estimate_background_color(
    image: Image.Image,
    *,
    x_start: int,
    x_end: int,
    y_start: int,
    y_end: int,
) -> Tuple[int, int, int]:
    pixels = image.load()
    sample_points = [
        (x_start, y_start),
        (max(x_start, x_end - 1), y_start),
        (x_start, max(y_start, y_end - 1)),
        (max(x_start, x_end - 1), max(y_start, y_end - 1)),
        ((x_start + x_end) // 2, y_start),
        ((x_start + x_end) // 2, max(y_start, y_end - 1)),
    ]
    channels = [[], [], []]
    for x, y in sample_points:
        red, green, blue = pixels[x, y][:3]
        channels[0].append(red)
        channels[1].append(green)
        channels[2].append(blue)
    return tuple(sorted(channel)[len(channel) // 2] for channel in channels)  # type: ignore[return-value]


def _is_text_like_bbox(bbox: List[int]) -> bool:
    width, height = bbox[2], bbox[3]
    if height <= 0:
        return True
    return width / height > 2.0


def _component_bboxes(points: List[Tuple[int, int]]) -> List[List[int]]:
    remaining = set(points)
    bboxes = []
    while remaining:
        start = remaining.pop()
        stack = [start]
        component = [start]
        while stack:
            x, y = stack.pop()
            for neighbor_x in (x - 1, x, x + 1):
                for neighbor_y in (y - 1, y, y + 1):
                    neighbor = (neighbor_x, neighbor_y)
                    if neighbor not in remaining:
                        continue
                    remaining.remove(neighbor)
                    stack.append(neighbor)
                    component.append(neighbor)
        bbox = _bounding_box(component)
        if bbox:
            bboxes.append(bbox)
    return bboxes


def _projection_bands(*, start: int, end: int, counts: Counter, threshold: int) -> List[Tuple[int, int]]:
    bands = []
    band_start = None
    band_end = None
    for index in range(start, end):
        if counts[index] >= threshold:
            if band_start is None:
                band_start = index
            band_end = index
            continue
        if band_start is not None and band_end is not None:
            bands.append((band_start, band_end))
            band_start = None
            band_end = None
    if band_start is not None and band_end is not None:
        bands.append((band_start, band_end))
    return bands


def _refine_dense_submark_bbox(points: List[Tuple[int, int]], bbox: List[int]) -> List[int]:
    x, y, width, height = bbox
    if width < 70 or height < 70:
        return bbox

    component_points = [
        point
        for point in points
        if x <= point[0] < x + width and y <= point[1] < y + height
    ]
    if not component_points:
        return bbox

    row_counts = Counter(point_y for _, point_y in component_points)
    row_threshold = max(10, int(width * 0.1))
    row_bands = _projection_bands(
        start=y,
        end=y + height,
        counts=row_counts,
        threshold=row_threshold,
    )
    if not row_bands:
        return bbox

    dense_y_start, dense_y_end = max(row_bands, key=lambda band: band[1] - band[0])
    dense_height = dense_y_end - dense_y_start + 1
    sparse_top = dense_y_start - y
    if sparse_top < height * 0.35 or dense_height < height * 0.25:
        return bbox

    dense_points = [
        point
        for point in component_points
        if dense_y_start <= point[1] <= dense_y_end
    ]
    column_counts = Counter(point_x for point_x, _ in dense_points)
    column_threshold = max(8, int(dense_height * 0.25))
    column_bands = _projection_bands(
        start=x,
        end=x + width,
        counts=column_counts,
        threshold=column_threshold,
    )
    if not column_bands:
        return bbox

    dense_x_start, dense_x_end = max(column_bands, key=lambda band: band[1] - band[0])
    dense_width = dense_x_end - dense_x_start + 1
    if dense_width < width * 0.35 or dense_height < height * 0.35:
        return bbox
    return [dense_x_start, dense_y_start, dense_width, dense_height]


def _is_valid_logo_bbox(bbox: List[int], *, image_width: int, image_height: int) -> bool:
    if bbox[2] < image_width * 0.08 or bbox[3] < image_height * 0.08:
        return False
    return not _is_text_like_bbox(bbox)


def _center_graphic_bbox(image: Image.Image) -> Optional[List[int]]:
    width, height = image.size
    if width < 80 or height < 80:
        return None

    pixels = image.load()
    x_start = round(width * 0.28)
    x_end = round(width * 0.72)
    y_start = round(height * 0.25)
    y_end = round(height * 0.72)
    background = _estimate_background_color(
        image,
        x_start=x_start,
        x_end=x_end,
        y_start=y_start,
        y_end=y_end,
    )
    points: List[Tuple[int, int]] = []

    for y in range(y_start, y_end):
        for x in range(x_start, x_end):
            red, green, blue = pixels[x, y][:3]
            if _color_distance((red, green, blue), background) > 70 and _is_graphic_mark_pixel(red, green, blue):
                points.append((x, y))

    bbox = _bounding_box(points)
    if not bbox:
        return None

    image_area = max(1, width * height)
    bbox_area = bbox[2] * bbox[3]
    point_ratio = len(points) / image_area
    bbox_ratio = bbox_area / image_area
    if point_ratio < 0.015 or bbox_ratio > 0.38:
        return None
    if not _is_valid_logo_bbox(bbox, image_width=width, image_height=height):
        return None
    candidates = [
        component_bbox
        for component_bbox in _component_bboxes(points)
        if _is_valid_logo_bbox(component_bbox, image_width=width, image_height=height)
    ]
    if not candidates:
        return bbox
    selected = max(candidates, key=lambda value: value[2] * value[3])
    return _refine_dense_submark_bbox(points, selected)


def detect_logo_regions(image_path: Path, *, scene: str) -> List[Region]:
    if scene not in {"marketing", "ecommerce"} or not image_path.exists():
        return []

    with Image.open(image_path) as raw_image:
        image = raw_image.convert("RGB")
        bbox = _center_graphic_bbox(image)
    if bbox is None:
        return []
    return [
        {
            "type": "logo",
            "bbox": bbox,
            "confidence": 0.62,
            "source": "logo_detector_baseline",
            "policy": "preserve",
        }
    ]


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        print(json.dumps({"regions": []}))
        return 0
    image_path = Path(argv[0])
    scene = argv[1]
    print(json.dumps({"regions": detect_logo_regions(image_path, scene=scene)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
