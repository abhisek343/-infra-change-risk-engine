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
\n# TODO: Implement advanced scoring algorithms\n