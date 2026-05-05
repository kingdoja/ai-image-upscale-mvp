from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, validator


Scale = Literal[2, 4]
Mode = Literal["faithful", "realistic", "both"]
Scene = Literal["product", "marketing", "ecommerce", "other"]
Status = Literal["queued", "running", "completed", "failed"]
RiskLevel = Literal["low", "medium", "high"]
ResultType = Literal["faithful", "realistic", "sharpened", "swinir", "hat", "material_guard"]
SelectedCandidate = Literal["faithful", "swinir", "hat"]

ALLOWED_ISSUES = {
    "good",
    "text_blur",
    "logo_error",
    "structure_changed",
    "oversharpen",
    "fake_texture",
    "color_shift",
    "too_slow",
    "other",
}


class JobCreateResponse(BaseModel):
    job_id: str
    status: Status
    estimated_seconds: int


class BatchCreateResponse(BaseModel):
    batch_id: str
    job_ids: List[str]
    created_count: int


class ResultRead(BaseModel):
    id: str
    type: ResultType
    url: str
    thumbnail_url: str
    model_name: str
    model_version: str
    quality_score: float
    risk_level: RiskLevel


class ProtectedRegionRead(BaseModel):
    type: str
    bbox: Optional[List[int]] = None
    confidence: float
    source: str
    policy: str


class ImageUnderstandingRead(BaseModel):
    controller_version: str
    scene: str
    detected_risks: List[str]
    degradation_types: List[str]
    subject_hints: List[str]
    review_required: bool
    data_usage_policy: str
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    detected_regions: List[ProtectedRegionRead]


class UpscalePlanRead(BaseModel):
    policy_version: str
    candidate_types: List[ResultType]
    protected_regions: List[str]
    protected_region_details: List[ProtectedRegionRead]
    enhancement_policy: str
    warnings: List[str]


class RoutingDecisionRead(BaseModel):
    policy_version: str
    candidate_types: List[ResultType]
    reasons: List[str]
    executed_candidate_types: List[ResultType]
    skipped_candidate_types: List[ResultType]
    skip_reasons: Dict[str, str]


class DataGovernanceRead(BaseModel):
    usage_scope: str
    training_state: str
    retention_policy: str
    requires_approval_for_training: bool


class ModelStatusRead(BaseModel):
    id: SelectedCandidate
    label: str
    backend: str
    status: Literal["ready", "demo", "disabled", "missing_config"]
    configured: bool
    detail: str


class ModelStatusListRead(BaseModel):
    models: List[ModelStatusRead]


class JobRead(BaseModel):
    job_id: str
    status: Status
    scale: int
    mode: str
    selected_candidates: List[SelectedCandidate]
    original_url: str
    warnings: List[str]
    results: List[ResultRead]
    understanding: ImageUnderstandingRead
    upscale_plan: UpscalePlanRead
    routing_decision: RoutingDecisionRead
    data_governance: DataGovernanceRead


class JobSummaryRead(BaseModel):
    job_id: str
    status: Status
    scale: int
    mode: str
    scene: str
    warnings: List[str]
    result_count: int
    thumbnail_url: Optional[str] = None
    result_url: Optional[str] = None
    risk_level: RiskLevel
    created_at: datetime


class JobListRead(BaseModel):
    jobs: List[JobSummaryRead]


class FeedbackCreate(BaseModel):
    selected_result_id: str
    rating: int = Field(ge=1, le=5)
    usable: bool
    issues: List[str] = Field(default_factory=list)
    comment: str = ""

    @validator("issues")
    def validate_issues(cls, issues: List[str]) -> List[str]:
        invalid = sorted(set(issues) - ALLOWED_ISSUES)
        if invalid:
            raise ValueError(f"Invalid issue tags: {', '.join(invalid)}")
        return issues


class FeedbackRead(BaseModel):
    id: str
    job_id: str
    selected_result_id: str
    rating: int
    usable: bool
    issues: List[str]
    comment: str
    created_at: datetime
