import json

from app.services.cost_engine import estimate_cost
from app.services.explanation_engine import (
    build_highlights,
    build_recommendations,
    build_review_checklist,
    summarize_report,
)
from app.services.graph_engine import build_blast_radius
from app.services.kubernetes_parser import parse_kubernetes_manifest
from app.services.policy_engine import evaluate_policies
from app.services.risk_engine import score_risk
from app.services.terraform_parser import parse_terraform_plan


def run_analysis(environment: str, terraform_plan: str | None, kubernetes_manifest: str | None) -> dict:
    terraform_resources = parse_terraform_plan(terraform_plan)
    kubernetes_resources = parse_kubernetes_manifest(kubernetes_manifest)
    resources = terraform_resources + kubernetes_resources

    blast_radius = build_blast_radius(resources)
    findings = evaluate_policies(resources, environment)
    cost = estimate_cost(resources)
    decision = score_risk(environment, resources, findings, blast_radius, cost)
    summary = summarize_report(environment, resources, findings, decision, cost, blast_radius)
    recommendations = build_recommendations(resources, findings, environment, cost)
    highlights = build_highlights(resources, findings, cost, blast_radius)
    review_checklist = build_review_checklist(findings, decision)

    return {
        "decision": {
            "score": decision["score"],
            "decision": decision["decision"],
            "confidence": decision["confidence"],
        },
        "summary": summary,
        "blast_radius": {
            "size": blast_radius["size"],
            "touched_domains": blast_radius["touched_domains"],
            "impacted_domains": blast_radius["impacted_domains"],
        },
        "cost": cost,
        "violations": [
            {
                "code": finding.code,
                "title": finding.title,
                "severity": finding.severity,
                "message": finding.message,
                "evidence": finding.evidence,
            }
            for finding in findings
        ],
        "evidence": [
            f"{resource.identifier} ({resource.resource_type}) -> {resource.action}"
            for resource in resources[:12]
        ],
        "affected_domains": blast_radius["impacted_domains"],
        "graph": {"nodes": blast_radius["nodes"], "edges": blast_radius["edges"]},
        "score_breakdown": decision["breakdown"],
        "recommendations": recommendations,
        "highlights": highlights,
        "review_checklist": review_checklist,
        "artifact_summary": {
            "terraform_changes": len(terraform_resources),
            "kubernetes_changes": len(kubernetes_resources),
            "total_changes": len(resources),
        },
        "resources": [
            {
                "source": resource.source,
                "identifier": resource.identifier,
                "resource_type": resource.resource_type,
                "action": resource.action,
                "domain": resource.domain,
                "criticality": resource.criticality,
                "monthly_cost_delta": round(resource.monthly_cost_delta, 2),
                "metadata": resource.metadata,
            }
            for resource in resources
        ],
    }


def serialize_report(report: dict) -> str:
    return json.dumps(report, indent=2)
