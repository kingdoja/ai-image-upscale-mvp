from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from PIL import Image

from .config import get_settings


@dataclass(frozen=True)
class QualityBreakdown:
    clarity: float
    structure: float
    logo_text: float
    material: float
    color: float
    hallucination_risk: float


@dataclass(frozen=True)
class QualityResult:
    risk_level: str
    quality_score: float
    warnings: List[str]
    breakdown: QualityBreakdown


def clamp_score(value: float) -> float:
    return max(0.0, min(1.0, round(value, 2)))


def evaluate_image(
    input_path: Path,
    result_path: Optional[Path] = None,
    *,
    contains_text: bool = False,
    contains_logo: bool = False,
    structural_risk: bool = False,
) -> QualityResult:
    warnings = []
    risk = "low"

    if not input_path.exists():
        return QualityResult(
            risk_level="high",
            quality_score=0.4,
            warnings=["input_missing"],
            breakdown=QualityBreakdown(
                clarity=0.4,
                structure=0.4,
                logo_text=0.4,
                material=0.4,
                color=0.4,
                hallucination_risk=0.8,
            ),
        )

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

    if structural_risk:
        warnings.append("structure_region_requires_review")
        risk = "high"

    score = 0.8
    if risk == "medium":
        score -= 0.2
    elif risk == "high":
        score -= 0.4
    quality_score = clamp_score(score)
    return QualityResult(
        risk_level=risk,
        quality_score=quality_score,
        warnings=warnings,
        breakdown=QualityBreakdown(
            clarity=quality_score,
            structure=0.4 if structural_risk or risk == "high" else 0.8,
            logo_text=0.5 if contains_text or contains_logo else 0.8,
            material=0.6 if risk != "low" else 0.8,
            color=0.7 if risk != "low" else 0.8,
            hallucination_risk=0.8 if risk == "high" else 0.4 if risk == "medium" else 0.1,
        ),
    )
