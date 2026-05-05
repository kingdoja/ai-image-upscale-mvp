from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple

from PIL import Image
from pydantic import BaseModel, Field

from .config import get_settings
from .vision_regions import VisionRegion, detect_protected_regions


CandidateType = Literal["faithful", "realistic", "swinir", "hat"]
SelectableCandidateType = Literal["faithful", "swinir", "hat"]
DEFAULT_SELECTED_CANDIDATES: List[SelectableCandidateType] = ["faithful", "swinir", "hat"]
CANDIDATE_DISPLAY_ORDER = ["faithful", "swinir", "hat", "realistic"]
CONTROLLER_VERSION = "semantic-controller-v0.10.0"
ROUTING_POLICY_VERSION = "routing-policy-v0.10.0"


class ModelCapability(BaseModel):
    candidate_type: CandidateType
    strengths: List[str]
    limitations: List[str]
    hallucination_risk: str
    expected_latency: str
    requires_manual_review: bool


class ProtectedRegionDetail(BaseModel):
    type: str
    bbox: Optional[List[int]] = None
    confidence: float
    source: str
    policy: str


class DataGovernanceSummary(BaseModel):
    usage_scope: str
    training_state: str
    retention_policy: str
    requires_approval_for_training: bool


class ImageUnderstandingReport(BaseModel):
    controller_version: str
    scene: str
    detected_risks: List[str]
    degradation_types: List[str]
    subject_hints: List[str]
    review_required: bool
    data_usage_policy: str
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    detected_regions: List[VisionRegion] = Field(default_factory=list)


class UpscalePlan(BaseModel):
    policy_version: str
    candidate_types: List[CandidateType]
    protected_regions: List[str]
    protected_region_details: List[ProtectedRegionDetail]
    enhancement_policy: str
    warnings: List[str]


class RoutingDecision(BaseModel):
    policy_version: str
    candidate_types: List[CandidateType]
    reasons: List[str]
    executed_candidate_types: List[CandidateType] = Field(default_factory=list)
    skipped_candidate_types: List[CandidateType] = Field(default_factory=list)
    skip_reasons: Dict[str, str] = Field(default_factory=dict)


def get_model_capability_registry() -> Dict[str, ModelCapability]:
    return {
        "faithful": ModelCapability(
            candidate_type="faithful",
            strengths=["preserve_product_structure", "stable_edges", "low_hallucination"],
            limitations=["limited_missing_detail_recovery", "may_keep_source_artifacts"],
            hallucination_risk="low",
            expected_latency="medium",
            requires_manual_review=False,
        ),
        "realistic": ModelCapability(
            candidate_type="realistic",
            strengths=["photo_realistic_detail_recovery", "material_texture_enhancement"],
            limitations=["higher_hallucination_risk", "slower_runtime", "requires_review_for_brand_assets"],
            hallucination_risk="high",
            expected_latency="high",
            requires_manual_review=True,
        ),
        "swinir": ModelCapability(
            candidate_type="swinir",
            strengths=["transformer_sr_baseline", "detail_reconstruction_comparison"],
            limitations=["optional_runtime_not_bundled", "requires_configured_weights"],
            hallucination_risk="medium",
            expected_latency="high",
            requires_manual_review=True,
        ),
        "hat": ModelCapability(
            candidate_type="hat",
            strengths=["strong_transformer_sr_baseline", "fine_detail_comparison"],
            limitations=["optional_runtime_not_bundled", "requires_configured_weights"],
            hallucination_risk="medium",
            expected_latency="high",
            requires_manual_review=True,
        ),
    }


def build_data_governance_summary() -> DataGovernanceSummary:
    return DataGovernanceSummary(
        usage_scope="local_inference_and_evaluation",
        training_state="not_approved_for_training",
        retention_policy="local_project_storage",
        requires_approval_for_training=True,
    )


def _subject_hints_for_scene(scene: str) -> List[str]:
    hints = {
        "product": ["generic_product_subject"],
        "marketing": ["marketing_layout", "possible_brand_text"],
        "ecommerce": ["ecommerce_detail_image", "possible_product_specs"],
        "other": ["general_image_subject"],
    }
    return hints.get(scene, ["general_image_subject"])


def _scene_risks(scene: str) -> List[str]:
    if scene in {"marketing", "ecommerce"}:
        return ["text_region_requires_review", "logo_region_requires_review"]
    return []


def _layout_bbox(scene: str, region_type: str, image_width: Optional[int], image_height: Optional[int]) -> Optional[List[int]]:
    if not image_width or not image_height:
        return None
    if region_type == "logo":
        return [0, 0, max(1, round(image_width * 0.25)), max(1, round(image_height * 0.18))]
    if region_type == "text":
        y_ratio = 0.62 if scene == "ecommerce" else 0.55
        y = min(image_height - 1, max(0, round(image_height * y_ratio)))
        return [0, y, image_width, max(1, image_height - y)]
    return None


def _protected_region_detail(report: ImageUnderstandingReport, region_type: str) -> ProtectedRegionDetail:
    for detected_region in report.detected_regions:
        if detected_region.type == region_type:
            return ProtectedRegionDetail(
                type=detected_region.type,
                bbox=detected_region.bbox,
                confidence=detected_region.confidence,
                source=detected_region.source,
                policy=detected_region.policy,
            )
    bbox = _layout_bbox(report.scene, region_type, report.image_width, report.image_height)
    return ProtectedRegionDetail(
        type=region_type,
        bbox=bbox,
        confidence=0.6 if bbox else 0.4,
        source="layout_heuristic" if bbox else "scene_rule",
        policy="preserve",
    )


def understand_image(input_path: Path, *, scene: str) -> ImageUnderstandingReport:
    degradation_types: List[str] = []
    detected_risks: List[str] = _scene_risks(scene)

    if not input_path.exists():
        return ImageUnderstandingReport(
            controller_version=CONTROLLER_VERSION,
            scene=scene,
            detected_risks=["input_missing"] + detected_risks,
            degradation_types=["unknown_input"],
            subject_hints=_subject_hints_for_scene(scene),
            review_required=True,
            data_usage_policy="inference_only",
        )

    with Image.open(input_path) as image:
        width, height = image.size
        if max(width, height) < 1024:
            degradation_types.append("low_resolution_input")
        if image.format and image.format.upper() in {"JPEG", "JPG", "WEBP"}:
            degradation_types.append("compressed_source")
    settings = get_settings()
    detected_regions = detect_protected_regions(
        input_path,
        scene=scene,
        backend=settings.region_detector_backend,
        external_command=settings.region_detector_command,
        tesseract_command=settings.tesseract_command,
        logo_detector_backend=settings.logo_detector_backend,
        logo_detector_command=settings.logo_detector_command,
        timeout_seconds=settings.region_detector_timeout_seconds,
    )

    return ImageUnderstandingReport(
        controller_version=CONTROLLER_VERSION,
        scene=scene,
        detected_risks=detected_risks,
        degradation_types=degradation_types or ["standard_resolution_input"],
        subject_hints=_subject_hints_for_scene(scene),
        review_required=bool(detected_risks),
        data_usage_policy="inference_only",
        image_width=width,
        image_height=height,
        detected_regions=detected_regions,
    )


def _ordered_candidates(candidate_types: List[str]) -> List[CandidateType]:
    unique = list(dict.fromkeys(candidate_types))
    return sorted(unique, key=lambda candidate_type: CANDIDATE_DISPLAY_ORDER.index(candidate_type))


def create_upscale_plan(
    report: ImageUnderstandingReport,
    *,
    requested_mode: str,
    selected_candidates: Optional[List[SelectableCandidateType]] = None,
) -> UpscalePlan:
    if requested_mode == "faithful":
        candidate_types: List[CandidateType] = ["faithful"]
    elif requested_mode == "both":
        candidate_types = ["faithful", "realistic", "swinir", "hat"]
    elif requested_mode == "realistic" and report.review_required:
        candidate_types = ["faithful", "realistic"]
    elif requested_mode == "realistic":
        candidate_types = ["realistic"]
    else:
        candidate_types = ["faithful"]
    if selected_candidates is not None:
        candidate_types = _ordered_candidates(selected_candidates)

    protected_regions: List[str] = []
    protected_region_details: List[ProtectedRegionDetail] = []
    if report.detected_regions:
        for detected_region in report.detected_regions:
            if detected_region.type not in protected_regions:
                protected_regions.append(detected_region.type)
                protected_region_details.append(_protected_region_detail(report, detected_region.type))
    if "text_region_requires_review" in report.detected_risks and "text" not in protected_regions:
        protected_regions.append("text")
        protected_region_details.append(_protected_region_detail(report, "text"))
    if "logo_region_requires_review" in report.detected_risks and "logo" not in protected_regions:
        protected_regions.append("logo")
        protected_region_details.append(_protected_region_detail(report, "logo"))

    warnings = list(report.detected_risks)
    if report.detected_regions:
        warnings.append("vision_regions_detected")
    if report.review_required:
        warnings.append("manual_review_required")

    return UpscalePlan(
        policy_version=ROUTING_POLICY_VERSION,
        candidate_types=candidate_types,
        protected_regions=protected_regions,
        protected_region_details=protected_region_details,
        enhancement_policy="conservative_preserve_structure" if report.review_required else "balanced_detail_enhancement",
        warnings=warnings,
    )


def build_routing_decision(plan: UpscalePlan, *, requested_mode: str) -> RoutingDecision:
    reasons = [f"requested_mode:{requested_mode}", f"policy:{plan.enhancement_policy}"]
    if plan.protected_regions:
        reasons.append("protected_risk_regions")
    if "realistic" in plan.candidate_types:
        reasons.append("realistic_candidate_is_review_only")
    return RoutingDecision(
        policy_version=ROUTING_POLICY_VERSION,
        candidate_types=plan.candidate_types,
        reasons=reasons,
    )


def build_semantic_context(
    input_path: Path,
    *,
    scene: str,
    requested_mode: str,
    selected_candidates: Optional[List[SelectableCandidateType]] = None,
) -> Tuple[
    ImageUnderstandingReport,
    UpscalePlan,
    RoutingDecision,
]:
    report = understand_image(input_path, scene=scene)
    plan = create_upscale_plan(report, requested_mode=requested_mode, selected_candidates=selected_candidates)
    routing = build_routing_decision(plan, requested_mode=requested_mode)
    return report, plan, routing
