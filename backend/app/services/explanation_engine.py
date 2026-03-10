from app.services.types import Finding, ResourceChange


def summarize_report(environment: str, resources: list[ResourceChange], findings: list[Finding], decision: dict, cost: dict, blast_radius: dict) -> str:
    domains = ", ".join(blast_radius.get("touched_domains", [])) or "platform"
    first_sentence = (
        f"This {environment} change was rated {decision['decision']} with a score of "
        f"{decision['score']}/100 because it touches {domains} infrastructure."
    )
    if findings:
        top_findings = ", ".join(finding.title.lower() for finding in findings[:3])
        second_sentence = f"Key issues include {top_findings}."
    else:
        second_sentence = "No blocking policy findings were detected."

    cost_sentence = ""
    if cost.get("monthly_delta"):
        cost_sentence = f" Estimated monthly delta is ${cost['monthly_delta']:.2f}."

    evidence_sentence = ""
    if decision["reasons"]:
        evidence_sentence = " Main risk drivers: " + "; ".join(decision["reasons"]) + "."

    return first_sentence + " " + second_sentence + cost_sentence + evidence_sentence


def build_recommendations(
    resources: list[ResourceChange], findings: list[Finding], environment: str, cost: dict
) -> list[dict[str, str]]:
    recommendations: list[dict[str, str]] = []
    if any(finding.code == "NET-001" for finding in findings):
        recommendations.append(
            {
                "title": "Restrict ingress exposure",
                "priority": "P0",
                "action": "Replace public CIDRs with service-to-service or VPC-scoped ingress before deploy.",
            }
        )
    if any(finding.code.startswith("IAM-") for finding in findings):
        recommendations.append(
            {
                "title": "Tighten IAM permissions",
                "priority": "P0",
                "action": "Scope IAM actions and resources to the minimum deploy paths needed for the rollout.",
            }
        )
    if any(finding.code.startswith("K8S-00") for finding in findings):
        recommendations.append(
            {
                "title": "Harden Kubernetes workloads",
                "priority": "P1",
                "action": "Add pinned image tags, health probes, resource limits, and non-privileged security contexts.",
            }
        )
    if cost.get("monthly_delta", 0) >= 100:
        recommendations.append(
            {
                "title": "Review cost delta",
                "priority": "P1",
                "action": "Validate that the projected monthly increase is expected and approved by the service owner.",
            }
        )
    if environment == "prod":
        recommendations.append(
            {
                "title": "Use staged rollout controls",
                "priority": "P1",
                "action": "Gate production apply behind manual approval and validate rollback steps before execution.",
            }
        )
    return recommendations[:5]


def build_highlights(resources: list[ResourceChange], findings: list[Finding], cost: dict, blast_radius: dict) -> list[str]:
    highlights: list[str] = []
    if findings:
        highlights.append(f"{len(findings)} policy/security findings detected.")
    if blast_radius.get("size", 0):
        highlights.append(
            f"Blast radius spans {blast_radius.get('size', 0)} nodes across {len(blast_radius.get('impacted_domains', []))} domains."
        )
    if cost.get("monthly_delta"):
        highlights.append(f"Projected monthly cost delta is ${cost['monthly_delta']:.2f}.")
    if any(resource.domain == "identity" for resource in resources):
        highlights.append("Identity-sensitive infrastructure is part of the change set.")
    return highlights


def build_review_checklist(findings: list[Finding], decision: dict) -> list[str]:
    checklist = [
        "Confirm rollback steps for the changed resources.",
        "Validate owners for every affected domain.",
        "Check alerting and health visibility before rollout.",
    ]
    if findings:
        checklist.append("Review and resolve all critical and high-severity findings.")
    if decision.get("decision") in {"MANUAL_REVIEW", "BLOCK"}:
        checklist.append("Require an approver sign-off before apply.")
    return checklist


def render_markdown_report(job_name: str, environment: str, report: dict, approvals: list[dict]) -> str:
    lines = [
        f"# {job_name}",
        "",
        f"- **Environment:** {environment}",
        f"- **Decision:** {report['decision']['decision']}",
        f"- **Score:** {report['decision']['score']}/100",
        f"- **Confidence:** {report['decision']['confidence']}",
        "",
        "## Summary",
        "",
        report["summary"],
        "",
        "## Highlights",
        "",
    ]
    lines.extend([f"- {line}" for line in report.get("highlights", [])] or ["- No highlights available."])
    lines.extend(["", "## Score breakdown", ""])
    for factor in report.get("score_breakdown", []):
        lines.append(f"- **{factor['label']}** (+{factor['weight']}): {factor['reason']}")
    lines.extend(["", "## Recommendations", ""])
    for rec in report.get("recommendations", []):
        lines.append(f"- **{rec['priority']} · {rec['title']}** — {rec['action']}")
    lines.extend(["", "## Violations", ""])
    for finding in report.get("violations", []):
        lines.append(f"- **{finding['severity'].upper()} {finding['code']}** — {finding['message']}")
    lines.extend(["", "## Approvals", ""])
    if approvals:
        for approval in approvals:
            note = f" — {approval['note']}" if approval.get("note") else ""
            lines.append(f"- **{approval['decision']}** by {approval['reviewer']}{note}")
    else:
        lines.append("- No approvals recorded.")
    return "\n".join(lines)
