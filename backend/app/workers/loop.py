import json
import time
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.config import WORKER_POLL_INTERVAL_SECONDS
from app.db.session import Base, SessionLocal, engine
from app.models import AnalysisJob
from app.services.analyzer import run_analysis, serialize_report


def process_once() -> bool:
    with SessionLocal() as db:
        job = db.scalars(
            select(AnalysisJob).where(AnalysisJob.status == "pending").order_by(AnalysisJob.created_at.asc())
        ).first()
        if not job:
            return False

        job.status = "running"
        job.started_at = datetime.now(UTC)
        job.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(job)

        try:
            report = run_analysis(job.environment, job.terraform_plan, job.kubernetes_manifest)
            job.report_json = serialize_report(report)
            job.status = "completed"
            job.completed_at = datetime.now(UTC)
            job.updated_at = datetime.now(UTC)
            job.error_text = None

            # Auto-generate LLM fix patches for any violations found.
            violations = report.get("violations", [])
            if violations:
                try:
\nprint('Starting worker loop debug')\n