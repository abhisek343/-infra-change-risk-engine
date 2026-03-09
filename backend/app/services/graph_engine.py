from collections import defaultdict
from typing import Any

from app.services.types import ResourceChange


DOMAIN_NEIGHBORS = {
    "network": ["edge", "compute", "data"],
    "edge": ["network", "compute"],
    "compute": ["edge", "data", "platform"],
    "data": ["compute", "network"],
    "identity": ["platform", "compute"],
    "storage": ["data", "compute"],
    "platform": ["compute", "identity"],
}


def build_blast_radius(resources: list[ResourceChange]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    touched_domains = {resource.domain for resource in resources}

    for domain in sorted(touched_domains):
        nodes.append({"id": f"domain:{domain}", "label": domain.title(), "category": "domain", "changed": False})

    for resource in resources:
        nodes.append(
            {
                "id": resource.identifier,
                "label": resource.identifier.split("/")[-1],
                "category": resource.domain,
                "changed": True,
            }
        )
        edges.append({"source": resource.identifier, "target": f"domain:{resource.domain}", "relation": "belongs_to"})

    by_domain: dict[str, list[str]] = defaultdict(list)
    for resource in resources:
        by_domain[resource.domain].append(resource.identifier)

    for domain, identifiers in by_domain.items():
        for neighbor in DOMAIN_NEIGHBORS.get(domain, []):
            if neighbor in touched_domains:
                edges.append({"source": f"domain:{domain}", "target": f"domain:{neighbor}", "relation": "blast_radius"})
        if len(identifiers) > 1:
            for idx in range(len(identifiers) - 1):
                edges.append({"source": identifiers[idx], "target": identifiers[idx + 1], "relation": "same_domain"})

    impacted_domains = sorted(touched_domains.union(*[set(DOMAIN_NEIGHBORS.get(domain, [])) for domain in touched_domains]))
    return {
        "nodes": nodes,
        "edges": edges,
        "touched_domains": sorted(touched_domains),
        "impacted_domains": impacted_domains,
        "size": len(resources) + len(impacted_domains),
    }

