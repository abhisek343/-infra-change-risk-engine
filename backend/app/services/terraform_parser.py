import json
from typing import Any

from app.services.types import ResourceChange


DOMAIN_MAP = {
    "aws_security_group": "network",
    "aws_security_group_rule": "network",
    "aws_lb": "edge",
    "aws_nat_gateway": "network",
    "aws_instance": "compute",
    "aws_launch_template": "compute",
    "aws_autoscaling_group": "compute",
    "aws_db_instance": "data",
    "aws_db_subnet_group": "data",
    "aws_iam_policy": "identity",
    "aws_iam_role_policy": "identity",
    "aws_s3_bucket": "storage",
}

CRITICALITY_MAP = {
    "network": "high",
    "data": "high",
    "identity": "high",
    "edge": "medium",
    "compute": "medium",
    "storage": "medium",
}

INSTANCE_PRICES = {
    "t3.medium": 30,
    "m6i.large": 70,
    "m6i.xlarge": 140,
    "m6i.2xlarge": 280,
    "db.t3.medium": 72,
    "db.m6i.large": 146,
    "db.m6i.xlarge": 292,
}


def _domain_for(resource_type: str) -> str:
    for key, domain in DOMAIN_MAP.items():
        if resource_type.startswith(key):
            return domain
    return "platform"


def _cost_delta(resource_type: str, before: dict[str, Any], after: dict[str, Any]) -> float:
    if resource_type == "aws_instance":
        before_price = INSTANCE_PRICES.get(before.get("instance_type"), 0)
        after_price = INSTANCE_PRICES.get(after.get("instance_type"), before_price)
        return float(after_price - before_price)
    if resource_type == "aws_db_instance":
        before_price = INSTANCE_PRICES.get(before.get("instance_class"), 0)
        after_price = INSTANCE_PRICES.get(after.get("instance_class"), before_price)
        return float(after_price - before_price)
    if resource_type == "aws_nat_gateway":
        return 32.0 if after else 0.0
    if resource_type == "aws_lb":
        return 25.0 if after else 0.0
    if resource_type == "aws_ebs_volume":
        before_size = before.get("size", 0) or 0
        after_size = after.get("size", before_size) or 0
        return max(float(after_size - before_size) * 0.08, 0.0)
    return 0.0


def parse_terraform_plan(terraform_plan: str | None) -> list[ResourceChange]:
    if not terraform_plan or not terraform_plan.strip():
        return []

    payload = json.loads(terraform_plan)
    changes = payload.get("resource_changes", [])
    parsed: list[ResourceChange] = []
    for resource in changes:
        change = resource.get("change", {})
        actions = change.get("actions", [])
        action = "/".join(actions) if actions else "unknown"
        before = change.get("before") or {}
        after = change.get("after") or {}
        resource_type = resource.get("type", "unknown")
        domain = _domain_for(resource_type)
        parsed.append(
            ResourceChange(
                source="terraform",
                identifier=resource.get("address", resource.get("name", resource_type)),
                resource_type=resource_type,
                action=action,
                domain=domain,
                criticality=CRITICALITY_MAP.get(domain, "medium"),
                before=before,
                after=after,
                metadata={
                    "name": resource.get("name"),
                    "provider": resource.get("provider_name"),
                    "module_address": resource.get("module_address"),
                },
                monthly_cost_delta=_cost_delta(resource_type, before, after),
            )
        )
    return parsed

