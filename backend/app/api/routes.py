import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import SAMPLE_DIR
from app.db.session import get_db
from app.models import AnalysisJob, ApprovalDecision
from app.schemas.jobs import ApprovalRecord, ApprovalRequest, CreateJobRequest, DashboardResponse, FixPatch, JobResponse, SamplePayload
from app.services.explanation_engine import render_markdown_report


router = APIRouter()


def _job_response(job: AnalysisJob) -> JobResponse:
    fix_patches: list[FixPatch] = []
    if job.fix_patches_json:
        try:
            fix_patches = [FixPatch(**p) for p in json.loads(job.fix_patches_json)]
        except Exception:
            fix_patches = []

    return JobResponse(
        id=job.id,
        name=job.name,
        environment=job.environment,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_text=job.error_text,
        report=json.loads(job.report_json) if job.report_json else None,
        approvals=[
            ApprovalRecord(
                id=approval.id,
                reviewer=approval.reviewer,
                decision=approval.decision,
                note=approval.note,
                created_at=approval.created_at,
            )
            for approval in job.approvals
        ],
        fix_patches=fix_patches,
    )


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "infra-change-risk-engine-backend"}


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(db: Session = Depends(get_db)) -> DashboardResponse:
    jobs = db.scalars(
        select(AnalysisJob).options(selectinload(AnalysisJob.approvals)).order_by(AnalysisJob.created_at.desc())
    ).all()
    totals = {
        "total": len(jobs),
        "pending": sum(1 for job in jobs if job.status == "pending"),
        "running": sum(1 for job in jobs if job.status == "running"),
        "completed": sum(1 for job in jobs if job.status == "completed"),
        "failed": sum(1 for job in jobs if job.status == "failed"),
    }
    decision_counts = {"APPROVE": 0, "WARN": 0, "MANUAL_REVIEW": 0, "BLOCK": 0}
    for job in jobs:
        report = json.loads(job.report_json) if job.report_json else None
        if report:
            decision = report.get("decision", {}).get("decision")
            if decision in decision_counts:
                decision_counts[decision] += 1
    return DashboardResponse(
        totals=totals,
        decision_counts=decision_counts,
        recent_jobs=[_job_response(job) for job in jobs[:8]],
    )


@router.get("/samples", response_model=list[SamplePayload])
def list_samples() -> list[SamplePayload]:
    sample_specs = [
        (
            "risky-prod-rollout",
            "Production rollout with public ingress, IAM broadening, database resize, and externally exposed Kubernetes resources.",
            SAMPLE_DIR / "terraform" / "risky-plan.json",
            SAMPLE_DIR / "k8s" / "risky-workload.yaml",
        ),
        (
            "safe-staging-rollout",
            "Lower-risk staging rollout with internal services, probes, and moderate cost impact.",
            SAMPLE_DIR / "terraform" / "safe-plan.json",
            SAMPLE_DIR / "k8s" / "safe-workload.yaml",
        ),
    ]
    payloads: list[SamplePayload] = []
    for name, description, tf_path, k8s_path in sample_specs:
        payloads.append(
            SamplePayload(
                name=name,
                description=description,
                terraform_plan=Path(tf_path).read_text(encoding="utf-8"),
                kubernetes_manifest=Path(k8s_path).read_text(encoding="utf-8"),
            )
        )
    return payloads


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(db: Session = Depends(get_db)) -> list[JobResponse]:
    jobs = db.scalars(
        select(AnalysisJob).options(selectinload(AnalysisJob.approvals)).order_by(AnalysisJob.created_at.desc())
    ).all()
    return [_job_response(job) for job in jobs]


