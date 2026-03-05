from app.services.types import ResourceChange


def estimate_cost(resources: list[ResourceChange]) -> dict:
    changed_resources = [
        {
            "resource": resource.identifier,
            "type": resource.resource_type,
            "monthly_delta": round(resource.monthly_cost_delta, 2),
        }
        for resource in resources
        if abs(resource.monthly_cost_delta) > 0
    ]
    monthly_delta = round(sum(item["monthly_delta"] for item in changed_resources), 2)
    return {"monthly_delta": monthly_delta, "changed_resources": changed_resources}

