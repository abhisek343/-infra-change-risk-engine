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
                    from app.agents.fix_agent import generate_fixes
                    patches = generate_fixes(violations, job.terraform_plan, job.kubernetes_manifest)
                    job.fix_patches_json = json.dumps(patches)
                except Exception as fix_exc:  # non-fatal — analysis result is still valid
                    print(f"Fix generation skipped for job {job.id}: {fix_exc}")

        except Exception as exc:  # surfaced in job status
            job.status = "failed"
            job.error_text = str(exc)
            job.completed_at = datetime.now(UTC)
            job.updated_at = datetime.now(UTC)
        db.commit()
        return True


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("Infra Change Risk Engine worker started. Polling for jobs...")
    while True:
        processed = process_once()
        if not processed:
            time.sleep(WORKER_POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
