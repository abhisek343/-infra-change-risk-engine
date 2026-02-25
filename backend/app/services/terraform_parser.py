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
