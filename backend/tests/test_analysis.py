import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.analyzer import run_analysis


client = TestClient(app)
ROOT = Path(__file__).resolve().parents[2]


def test_analysis_pipeline_blocks_risky_prod_rollout() -> None:
    terraform_plan = (ROOT / "samples" / "terraform" / "risky-plan.json").read_text(encoding="utf-8")
    kubernetes_manifest = (ROOT / "samples" / "k8s" / "risky-workload.yaml").read_text(encoding="utf-8")
    report = run_analysis("prod", terraform_plan, kubernetes_manifest)

    assert report["decision"]["decision"] in {"BLOCK", "MANUAL_REVIEW"}
    assert report["decision"]["score"] >= 70
    assert report["violations"]
    assert report["blast_radius"]["size"] >= 6


def test_api_job_creation_and_fetch() -> None:
    terraform_plan = (ROOT / "samples" / "terraform" / "safe-plan.json").read_text(encoding="utf-8")
    response = client.post(
        "/api/v1/jobs",
        json={
            "name": "safe rollout",
            "environment": "staging",
            "terraform_plan": terraform_plan,
            "kubernetes_manifest": "",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    job_id = payload["id"]

    get_response = client.get(f"/api/v1/jobs/{job_id}")
    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched["id"] == job_id
    assert fetched["status"] == "pending"


def test_dashboard_and_approval_flow() -> None:
    terraform_plan = (ROOT / "samples" / "terraform" / "risky-plan.json").read_text(encoding="utf-8")
    create_response = client.post(
        "/api/v1/jobs",
        json={
            "name": "approval flow",
            "environment": "prod",
            "terraform_plan": terraform_plan,
            "kubernetes_manifest": "",
        },
    )
    assert create_response.status_code == 200
    job_id = create_response.json()["id"]

    dashboard_response = client.get("/api/v1/dashboard")
    assert dashboard_response.status_code == 200
    dashboard_payload = dashboard_response.json()
    assert "totals" in dashboard_payload
    assert dashboard_payload["totals"]["total"] >= 1

    approval_response = client.post(
        f"/api/v1/jobs/{job_id}/approvals",
        json={"reviewer": "Abhisek", "decision": "WARN", "note": "Needs manual review."},
    )
    assert approval_response.status_code == 200
    approval_payload = approval_response.json()
    assert approval_payload["approvals"]
    assert approval_payload["approvals"][0]["decision"] == "WARN"
