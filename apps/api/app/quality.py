from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from PIL import Image

from .config import get_settings


@dataclass(frozen=True)
class QualityResult:
    risk_level: str
    quality_score: float
    warnings: List[str]


def clamp_score(value: float) -> float:
    return max(0.0, min(1.0, round(value, 2)))


def evaluate_image(
    input_path: Path,
    result_path: Optional[Path] = None,
    *,
    contains_text: bool = False,
    contains_logo: bool = False,
) -> QualityResult:
    warnings = []
    risk = "low"

    if not input_path.exists():
        return QualityResult(risk_level="high", quality_score=0.4, warnings=["input_missing"])

    with Image.open(input_path) as image:
        width, height = image.size
        if width * height > get_settings().max_input_pixels:
            risk = "high"
            warnings.append("input_too_large")

    if result_path is not None and not result_path.exists():
        risk = "high"
        warnings.append("result_missing")

    if contains_text:
        warnings.append("text_region_requires_review")
        if risk == "low":
            risk = "medium"

    if contains_logo:
        warnings.append("logo_region_requires_review")
        if risk == "low":
            risk = "medium"

    score = 0.8
    if risk == "medium":
        score -= 0.2
    elif risk == "high":
        score -= 0.4
    return QualityResult(risk_level=risk, quality_score=clamp_score(score), warnings=warnings)
