"""
MCP tool schema definitions.

Each entry in TOOLS describes one callable tool that the MCP server
exposes to AI agents. The schema follows the JSON Schema subset used
by the Model Context Protocol (MCP) tools/list response.
"""
from __future__ import annotations

from typing import Any

TOOLS: list[dict[str, Any]] = [
    {
        "name": "analyze_infrastructure",
        "description": (
            "Run the full Infra Change Risk Engine analysis pipeline on a Terraform plan "
            "and/or Kubernetes manifest. Returns a complete risk report including decision "
            "(APPROVE/WARN/MANUAL_REVIEW/BLOCK), risk score, policy violations, blast radius, "
            "cost delta, and per-violation LLM-generated fix patches."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "environment": {
                    "type": "string",
                    "enum": ["dev", "staging", "prod"],
                    "description": "Deployment environment — affects severity weights and score thresholds.",
                },
                "terraform_plan": {
                    "type": "string",
                    "description": "JSON string of a 'terraform show -json' plan output. Optional if kubernetes_manifest is provided.",
                },
                "kubernetes_manifest": {
                    "type": "string",
                    "description": "YAML string of one or more Kubernetes manifests (multi-doc OK). Optional if terraform_plan is provided.",
                },
            },
            "required": ["environment"],
        },
    },
    {
        "name": "list_policy_rules",
        "description": (
            "Return the full catalogue of deterministic policy rules built into the engine. "
            "Each rule has a code, title, severity, and the condition that triggers it. "
            "Use this tool to understand what the engine checks before submitting artifacts."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "generate_fixes",
        "description": (
            "Given a list of policy violations (as returned by analyze_infrastructure) and "
            "the original infrastructure artifacts, invoke the LLM fix-generation agent to "
            "produce corrected Terraform HCL or Kubernetes YAML patches for each violation. "
            "Requires OPENAI_API_KEY to be set on the server for live LLM patches; "
            "otherwise returns advisory-only text."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "violations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string"},
                            "title": {"type": "string"},
                            "severity": {"type": "string"},
                            "message": {"type": "string"},
                            "evidence": {"type": "object"},
                        },
                        "required": ["code", "title", "severity", "message"],
                    },
                    "description": "List of violation objects from a previous analyze_infrastructure call.",
                },
                "terraform_plan": {
                    "type": "string",
                    "description": "Original Terraform plan JSON (used to extract relevant snippet for the LLM).",
                },
                "kubernetes_manifest": {
                    "type": "string",
                    "description": "Original Kubernetes manifest YAML (used to extract relevant snippet for the LLM).",
                },
            },
            "required": ["violations"],
        },
    },
]

# Human-readable catalogue of every deterministic rule the policy engine evaluates.
POLICY_RULES: list[dict[str, str]] = [
    {
        "code": "NET-001",
        "title": "Public ingress exposure",
        "severity": "critical (prod) / high (other)",
        "trigger": "aws_security_group_rule with cidr_blocks = [\"0.0.0.0/0\"]",
    },
    {
        "code": "IAM-001",
        "title": "Wildcard IAM policy",
        "severity": "high",
        "trigger": "aws_iam_policy or aws_iam_role_policy with Action or Resource = \"*\"",
    },
    {
        "code": "K8S-001",
        "title": "Mutable image tag",
        "severity": "medium",
        "trigger": "Deployment/StatefulSet container image ends with ':latest'",
    },
    {
        "code": "K8S-002",
        "title": "Missing resource constraints",
        "severity": "medium",
        "trigger": "Deployment/StatefulSet container has no resources block",
    },
    {
        "code": "K8S-003",
        "title": "Privileged container",
        "severity": "critical",
        "trigger": "Container securityContext.privileged = true",
    },
    {
        "code": "K8S-004",
        "title": "Missing health probes",
        "severity": "high (prod) / medium (other)",
        "trigger": "Deployment/StatefulSet container missing readinessProbe or livenessProbe",
    },
    {
        "code": "K8S-005",
        "title": "Externally exposed service",
        "severity": "high",
        "trigger": "Service spec.type = LoadBalancer or NodePort",
    },
    {
        "code": "K8S-006",
        "title": "Ingress without TLS",
        "severity": "high",
        "trigger": "Ingress spec has no tls block",
    },
    {
        "code": "DATA-001",
        "title": "Production database modification",
        "severity": "high",
        "trigger": "aws_db_instance change in prod environment",
    },
]
