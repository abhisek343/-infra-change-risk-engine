from typing import Any

import yaml

from app.services.types import ResourceChange


def _criticality(kind: str) -> str:
    if kind in {"Ingress", "Service"}:
        return "high"
    if kind in {"Deployment", "StatefulSet"}:
        return "medium"
    return "low"


def _domain(kind: str) -> str:
    if kind in {"Ingress", "Service"}:
        return "edge"
    if kind in {"Deployment", "DaemonSet", "StatefulSet"}:
        return "compute"
    if kind in {"Secret", "Role", "RoleBinding", "ClusterRole", "ClusterRoleBinding"}:
        return "identity"
    return "platform"
\nprint('WIP: parsing k8s container blocks')\n