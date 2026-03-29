export type DecisionSummary = {
  score: number;
  decision: string;
  confidence: string;
};

export type ScoreFactor = {
  label: string;
  weight: number;
  reason: string;
};

export type Violation = {
  code: string;
  title: string;
  severity: string;
  message: string;
  evidence: Record<string, unknown>;
};

export type Recommendation = {
  title: string;
  priority: string;
  action: string;
};

export type ApprovalRecord = {
  id: string;
  reviewer: string;
  decision: string;
  note?: string | null;
  created_at: string;
};

export type FixPatch = {
  violation_code: string;
  violation_title: string;
  patch_type: string;   // "terraform" | "kubernetes" | "advisory"
  language: string;     // "hcl" | "yaml" | "json" | "text"
  patch_content: string;
  explanation: string;
  llm_model: string;
};

export type RiskReport = {
  decision: DecisionSummary;
  summary: string;
  blast_radius: {
    size: number;
    touched_domains: string[];
    impacted_domains: string[];
  };
  cost: {
    monthly_delta: number;
    changed_resources: Array<{
      resource: string;
      type: string;
      monthly_delta: number;
    }>;
  };
  violations: Violation[];
  evidence: string[];
  affected_domains: string[];
  graph: {
    nodes: Array<{ id: string; label: string; category: string; changed: boolean }>;
    edges: Array<{ source: string; target: string; relation: string }>;
  };
  score_breakdown: ScoreFactor[];
  recommendations: Recommendation[];
  highlights: string[];
  review_checklist: string[];
  artifact_summary: Record<string, number>;
  resources: Array<{
    source: string;
    identifier: string;
    resource_type: string;
    action: string;
    domain: string;
    criticality: string;
    monthly_cost_delta: number;
    metadata: Record<string, unknown>;
  }>;
};

export type Job = {
  id: string;
  name: string;
  environment: string;
  status: string;
  created_at: string;
  updated_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  error_text?: string | null;
  report?: RiskReport | null;
  approvals: ApprovalRecord[];
  fix_patches: FixPatch[];
};

export type DashboardData = {
  totals: Record<string, number>;
  decision_counts: Record<string, number>;
  recent_jobs: Job[];
};

export type Sample = {
  name: string;
  description: string;
  terraform_plan: string;
  kubernetes_manifest: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

export const api = {
  getDashboard: () => request<DashboardData>("/dashboard"),
  getSamples: () => request<Sample[]>("/samples"),
  getJobs: () => request<Job[]>("/jobs"),
  getJob: (jobId: string) => request<Job>(`/jobs/${jobId}`),
  createJob: (payload: {
    name: string;
    environment: string;
    terraform_plan: string;
    kubernetes_manifest: string;
  }) =>
    request<Job>("/jobs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  runJob: (jobId: string) =>
    request<Job>(`/jobs/${jobId}/run`, {
      method: "POST",
    }),
  addApproval: (
    jobId: string,
    payload: {
      reviewer: string;
      decision: string;
      note?: string;
    },
  ) =>
    request<Job>(`/jobs/${jobId}/approvals`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  triggerFixes: (jobId: string) =>
    request<FixPatch[]>(`/jobs/${jobId}/fixes`, { method: "POST" }),
  getFixes: (jobId: string) =>
    request<FixPatch[]>(`/jobs/${jobId}/fixes`),
};

export function markdownExportUrl(jobId: string): string {
  return `${API_BASE}/jobs/${jobId}/export.md`;
}

export function mcpEndpointUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
  return base.replace(/\/api\/v1$/, "") + "/mcp";
}
