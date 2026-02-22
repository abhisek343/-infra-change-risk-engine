from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResourceChange:
    source: str
    identifier: str
    resource_type: str
    action: str
    domain: str
    criticality: str
    before: dict[str, Any]
    after: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    monthly_cost_delta: float = 0.0


@dataclass
class Finding:
    code: str
    title: str
    severity: str
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)

