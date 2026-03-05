from app.services.types import Finding, ResourceChange


SEVERITY_WEIGHTS = {"low": 6, "medium": 12, "high": 20, "critical": 28}


def evaluate_policies(resources: list[ResourceChange], environment: str) -> list[Finding]:
    findings: list[Finding] = []
    for resource in resources:
        after = resource.after or {}
        if resource.resource_type == "aws_security_group_rule":
            cidr = after.get("cidr_blocks") or after.get("cidr_ipv4")
            if cidr == ["0.0.0.0/0"] or cidr == "0.0.0.0/0":
                findings.append(
                    Finding(
                        code="NET-001",
                        title="Public ingress exposure",
                        severity="critical" if environment == "prod" else "high",
                        message=f"{resource.identifier} opens ingress to 0.0.0.0/0.",
                        evidence={"resource": resource.identifier, "cidr": cidr},
                    )
                )
        if resource.resource_type in {"aws_iam_policy", "aws_iam_role_policy"}:
            policy_doc = str(after)
            if '"Action": "*"' in policy_doc or '"Resource": "*"' in policy_doc or "'Action': '*'" in policy_doc:
                findings.append(
                    Finding(
                        code="IAM-001",
                        title="Wildcard IAM policy",
                        severity="high",
                        message=f"{resource.identifier} introduces wildcard IAM permissions.",
                        evidence={"resource": resource.identifier},
                    )
                )
        if resource.source == "kubernetes":
            kind = resource.metadata.get("kind")
            if kind in {"Deployment", "StatefulSet"}:
                template = (((after.get("spec") or {}).get("template") or {}).get("spec") or {})
                containers = template.get("containers") or []
                for container in containers:
                    name = container.get("name", "container")
                    if str(container.get("image", "")).endswith(":latest"):
                        findings.append(
                            Finding(
                                code="K8S-001",
                                title="Mutable image tag",
                                severity="medium",
                                message=f"{name} uses the latest tag.",
                                evidence={"resource": resource.identifier, "container": name},
                            )
                        )
                    if not container.get("resources"):
                        findings.append(
                            Finding(
                                code="K8S-002",
                                title="Missing resource constraints",
                                severity="medium",
                                message=f"{name} has no resource requests or limits.",
                                evidence={"resource": resource.identifier, "container": name},
                            )
                        )
                    security_context = container.get("securityContext") or {}
                    if security_context.get("privileged") is True:
                        findings.append(
                            Finding(
                                code="K8S-003",
                                title="Privileged container",
                                severity="critical",
                                message=f"{name} is configured as privileged.",
                                evidence={"resource": resource.identifier, "container": name},
                            )
                        )
                pod_spec = ((after.get("spec") or {}).get("template") or {}).get("spec") or {}
                for container in pod_spec.get("containers") or []:
                    if not container.get("readinessProbe") or not container.get("livenessProbe"):
                        findings.append(
                            Finding(
                                code="K8S-004",
                                title="Missing health probes",
                                severity="high" if environment == "prod" else "medium",
                                message=f"{container.get('name', 'container')} is missing readiness or liveness probes.",
                                evidence={"resource": resource.identifier},
                            )
                        )
            if kind == "Service":
                service_type = (after.get("spec") or {}).get("type")
                if service_type in {"LoadBalancer", "NodePort"}:
                    findings.append(
                        Finding(
                            code="K8S-005",
                            title="Externally exposed service",
                            severity="high",
                            message=f"{resource.identifier} exposes traffic via {service_type}.",
                            evidence={"resource": resource.identifier, "service_type": service_type},
                        )
                    )
            if kind == "Ingress":
                tls = (after.get("spec") or {}).get("tls")
                if not tls:
                    findings.append(
                        Finding(
                            code="K8S-006",
                            title="Ingress without TLS",
                            severity="high",
                            message=f"{resource.identifier} does not define TLS.",
                            evidence={"resource": resource.identifier},
                        )
                    )
        if resource.resource_type == "aws_db_instance" and environment == "prod":
            findings.append(
                Finding(
                    code="DATA-001",
                    title="Production database modification",
                    severity="high",
                    message=f"{resource.identifier} changes a production database instance.",
                    evidence={"resource": resource.identifier},
                )
            )
    return findings

