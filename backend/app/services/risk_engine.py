from app.services.policy_engine import SEVERITY_WEIGHTS
from app.services.types import Finding, ResourceChange


def score_risk(
    environment: str,
    resources: list[ResourceChange],
    findings: list[Finding],
    blast_radius: dict,
    cost: dict,
) -> dict:
    score = 0
    reasons: list[str] = []
    breakdown: list[dict[str, int | str]] = []

    if environment == "prod":
        score += 20
        reasons.append("targets production")
        breakdown.append({"label": "Production environment", "weight": 20, "reason": "The change targets prod."})

    severity_total = 0
    for finding in findings:
        severity_total += SEVERITY_WEIGHTS.get(finding.severity, 0)
    violation_score = min(severity_total, 45)
    score += violation_score
    if violation_score:
        breakdown.append(
            {
                "label": "Policy and security findings",
                "weight": violation_score,
                "reason": f"{len(findings)} findings contributed to the risk score.",
            }
        )

    blast_size = int(blast_radius.get("size", 0))
    if blast_size >= 10:
        score += 15
        reasons.append("touches a large blast radius")
        breakdown.append(
            {"label": "Blast radius", "weight": 15, "reason": "The change impacts a large dependency surface."}
        )
    elif blast_size >= 6:
        score += 10
        reasons.append("touches multiple dependent domains")
        breakdown.append(
            {"label": "Blast radius", "weight": 10, "reason": "The change crosses multiple dependent domains."}
        )

    if cost.get("monthly_delta", 0) >= 250:
        score += 10
        reasons.append("introduces a notable monthly cost increase")
        breakdown.append(
            {"label": "Projected cost increase", "weight": 10, "reason": "The monthly delta exceeds $250."}
        )
    elif cost.get("monthly_delta", 0) >= 100:
        score += 6
        reasons.append("increases projected monthly cost")
        breakdown.append(
            {"label": "Projected cost increase", "weight": 6, "reason": "The monthly delta exceeds $100."}
        )

    if any(resource.domain in {"data", "identity"} for resource in resources):
        score += 8
        reasons.append("modifies stateful or identity-sensitive infrastructure")
        breakdown.append(
            {
                "label": "Sensitive infrastructure domains",
                "weight": 8,
                "reason": "The change modifies data or identity-related infrastructure.",
            }
        )

    score = min(score, 100)
    if score >= 80:
        decision = "BLOCK"
        confidence = "high"
    elif score >= 60:
        decision = "MANUAL_REVIEW"
        confidence = "high"
    elif score >= 30:
        decision = "WARN"
        confidence = "medium"
    else:
        decision = "APPROVE"
        confidence = "medium"

    return {
        "score": score,
        "decision": decision,
        "confidence": confidence,
        "reasons": reasons,
        "breakdown": breakdown,
    }
