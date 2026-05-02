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
  type: "faithful" | "realistic" | "sharpened";
  url: string;
  thumbnail_url: string;
  model_name: string;
  model_version: string;
  quality_score: number;
  risk_level: "low" | "medium" | "high";
};

export type JobRead = {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed";
  scale: number;
  mode: string;
  original_url: string;
  warnings: string[];
  results: ResultRead[];
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
