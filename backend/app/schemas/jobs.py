from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CreateJobRequest(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    environment: str = Field(default="staging", pattern="^(dev|staging|prod)$")
    terraform_plan: str | None = None
    kubernetes_manifest: str | None = None


class DecisionSummary(BaseModel):
    score: int
    decision: str
    confidence: str


class ScoreFactor(BaseModel):
    label: str
    weight: int
    reason: str


class Violation(BaseModel):
    code: str
    title: str
    severity: str
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class CostDelta(BaseModel):
    monthly_delta: float
    changed_resources: list[dict[str, Any]]


class GraphNode(BaseModel):
    id: str
    label: str
    category: str
    changed: bool = False


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str


class Recommendation(BaseModel):
    title: str
    priority: str
    action: str


class ApprovalRecord(BaseModel):
    id: str
    reviewer: str
    decision: str
    note: str | None = None
    created_at: datetime


class ApprovalRequest(BaseModel):
    reviewer: str = Field(min_length=2, max_length=80)
    decision: str = Field(pattern="^(APPROVE|WARN|BLOCK)$")
    note: str | None = Field(default=None, max_length=800)


class FixPatch(BaseModel):
    """A single LLM-generated corrective patch for one policy violation."""
    violation_code: str
    violation_title: str
    patch_type: str  # "terraform" | "kubernetes" | "advisory"
    language: str    # "hcl" | "yaml" | "json" | "text"
    patch_content: str
    explanation: str
    llm_model: str = ""


class RiskReport(BaseModel):
    decision: DecisionSummary
    summary: str
    blast_radius: dict[str, Any]
    cost: CostDelta
    violations: list[Violation]
    evidence: list[str]
    affected_domains: list[str]
    graph: dict[str, list[dict[str, Any]]]
    resources: list[dict[str, Any]]
    score_breakdown: list[ScoreFactor] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    review_checklist: list[str] = Field(default_factory=list)
    artifact_summary: dict[str, Any] = Field(default_factory=dict)


class JobResponse(BaseModel):
    id: str
    name: str
    environment: str
    status: str
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_text: str | None = None
    report: RiskReport | None = None
    approvals: list[ApprovalRecord] = Field(default_factory=list)
    fix_patches: list[FixPatch] = Field(default_factory=list)


class DashboardResponse(BaseModel):
    totals: dict[str, int]
    recent_jobs: list[JobResponse]
    decision_counts: dict[str, int]


class SamplePayload(BaseModel):
    name: str
    description: str
    terraform_plan: str
    kubernetes_manifest: str
