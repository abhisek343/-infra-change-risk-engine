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


def parse_kubernetes_manifest(kubernetes_manifest: str | None) -> list[ResourceChange]:
    if not kubernetes_manifest or not kubernetes_manifest.strip():
        return []

    documents = [doc for doc in yaml.safe_load_all(kubernetes_manifest) if isinstance(doc, dict)]
    changes: list[ResourceChange] = []
    for doc in documents:
        kind = str(doc.get("kind", "Unknown"))
        metadata = doc.get("metadata", {}) or {}
        spec = doc.get("spec", {}) or {}
        identifier = f"{metadata.get('namespace', 'default')}/{kind}/{metadata.get('name', 'unnamed')}"
        cost_delta = 0.0
        if kind == "Service" and spec.get("type") == "LoadBalancer":
            cost_delta += 18.0
        if kind in {"Deployment", "StatefulSet"}:
            replicas = int(spec.get("replicas", 1) or 1)
            cost_delta += max(replicas - 2, 0) * 12.0
        changes.append(
            ResourceChange(
                source="kubernetes",
                identifier=identifier,
                resource_type=kind.lower(),
                action="apply",
                domain=_domain(kind),
                criticality=_criticality(kind),
                before={},
                after=doc,
                metadata={"kind": kind, "name": metadata.get("name"), "namespace": metadata.get("namespace", "default")},
                monthly_cost_delta=cost_delta,
            )
        )
    return changes

