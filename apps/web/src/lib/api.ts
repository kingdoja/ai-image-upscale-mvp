const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export type CreateJobResponse = {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed";
  estimated_seconds: number;
};

export type BatchCreateResponse = {
  batch_id: string;
  job_ids: string[];
  created_count: number;
};

export type ResultRead = {
  id: string;
  type: "faithful" | "realistic" | "sharpened" | "swinir" | "hat" | "material_guard";
  url: string;
  thumbnail_url: string;
  model_name: string;
  model_version: string;
  quality_score: number;
  risk_level: "low" | "medium" | "high";
};

export type SelectableCandidate = "faithful" | "swinir" | "hat";

export type ImageUnderstandingRead = {
  controller_version: string;
  scene: string;
  detected_risks: string[];
  degradation_types: string[];
  subject_hints: string[];
  review_required: boolean;
  data_usage_policy: string;
  image_width: number | null;
  image_height: number | null;
  detected_regions: ProtectedRegionRead[];
};

export type ProtectedRegionRead = {
  type: string;
  bbox: number[] | null;
  confidence: number;
  source: string;
  policy: string;
};

export type UpscalePlanRead = {
  policy_version: string;
  candidate_types: ResultRead["type"][];
  protected_regions: string[];
  protected_region_details: ProtectedRegionRead[];
  enhancement_policy: string;
  warnings: string[];
};

export type RoutingDecisionRead = {
  policy_version: string;
  candidate_types: ResultRead["type"][];
  reasons: string[];
  executed_candidate_types: ResultRead["type"][];
  skipped_candidate_types: ResultRead["type"][];
  skip_reasons: Record<string, string>;
};

export type DataGovernanceRead = {
  usage_scope: string;
  training_state: string;
  retention_policy: string;
  requires_approval_for_training: boolean;
};

export type JobRead = {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed";
  scale: number;
  mode: string;
  selected_candidates: SelectableCandidate[];
  original_url: string;
  warnings: string[];
  results: ResultRead[];
  understanding: ImageUnderstandingRead;
  upscale_plan: UpscalePlanRead;
  routing_decision: RoutingDecisionRead;
  data_governance: DataGovernanceRead;
};

export type JobSummaryRead = {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed";
  scale: number;
  mode: string;
  scene: string;
  warnings: string[];
  result_count: number;
  thumbnail_url: string | null;
  result_url: string | null;
  risk_level: "low" | "medium" | "high";
  created_at: string;
};

export type JobListRead = {
  jobs: JobSummaryRead[];
};

export type ModelStatus = {
  id: SelectableCandidate;
  label: string;
  backend: string;
  status: "ready" | "demo" | "disabled" | "missing_config";
  configured: boolean;
  detail: string;
};

export type ModelStatusListRead = {
  models: ModelStatus[];
};

export async function createJob(formData: FormData): Promise<CreateJobResponse> {
  const response = await fetch(`${API_BASE_URL}/api/upscale/jobs`, {
    method: "POST",
    body: formData
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function createBatch(formData: FormData): Promise<BatchCreateResponse> {
  const response = await fetch(`${API_BASE_URL}/api/upscale/batches`, {
    method: "POST",
    body: formData
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export function batchDownloadUrl(batchId: string) {
  return `${API_BASE_URL}/api/upscale/batches/${batchId}/download`;
}

export function resultDownloadUrl(resultId: string) {
  return `${API_BASE_URL}/api/upscale/results/${resultId}/download`;
}

export function jobResultDownloadUrl(jobId: string) {
  return `${API_BASE_URL}/api/upscale/jobs/${jobId}/download`;
}

export function reportDownloadUrl(batchId: string, format: "markdown" | "csv" = "markdown") {
  return `${API_BASE_URL}/api/upscale/reports/${batchId}?format=${format}`;
}

export function riskSamplesDownloadUrl(batchId: string, format: "markdown" | "csv" = "csv") {
  return `${API_BASE_URL}/api/upscale/reports/${batchId}/risk-samples?format=${format}`;
}

export async function listJobs(): Promise<JobListRead> {
  const response = await fetch(`${API_BASE_URL}/api/upscale/jobs`);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function getModelStatuses(): Promise<ModelStatusListRead> {
  const response = await fetch(`${API_BASE_URL}/api/upscale/models/status`);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function getJob(jobId: string): Promise<JobRead> {
  const response = await fetch(`${API_BASE_URL}/api/upscale/jobs/${jobId}`);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function processJob(jobId: string): Promise<JobRead> {
  const response = await fetch(`${API_BASE_URL}/api/upscale/jobs/${jobId}/process`, {
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function submitFeedback(jobId: string, payload: unknown) {
  const response = await fetch(`${API_BASE_URL}/api/upscale/jobs/${jobId}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export function assetUrl(path: string) {
  if (path.startsWith("http")) {
    return path;
  }
  return `${API_BASE_URL}${path}`;
}
