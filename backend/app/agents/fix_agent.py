"""
LLM fix-generation agent.

For each policy violation detected by the deterministic engine, this agent
calls an OpenAI-compatible LLM to produce a corrected Terraform HCL or
Kubernetes YAML patch. Results are returned as structured FixPatch objects.

Set OPENAI_API_KEY (and optionally OPENAI_BASE_URL / LLM_MODEL) to enable.
Without a key the agent returns advisory-only patches with no LLM call.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.core.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Per-violation prompt templates
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are an expert infrastructure security engineer. "
    "Given a policy violation and the relevant infrastructure artifact snippet, "
    "produce a minimal corrective patch that resolves ONLY the stated violation. "
    "Return JSON with exactly these keys: "
    '{"patch_content": "<corrected code>", "explanation": "<one sentence why>"} '
    "and nothing else. Do not wrap in markdown fences."
)

_VIOLATION_CONTEXT: dict[str, dict[str, str]] = {
    "NET-001": {
        "patch_type": "terraform",
        "language": "hcl",
        "user_prefix": (
            "The Terraform aws_security_group_rule below opens ingress to 0.0.0.0/0. "
            "Rewrite it so cidr_blocks is restricted to a private VPC CIDR (e.g. 10.0.0.0/8) "
            "or replaced by a source_security_group_id reference.\n\n"
        ),
    },
    "IAM-001": {
        "patch_type": "terraform",
        "language": "json",
        "user_prefix": (
            "The IAM policy document below uses wildcard Action or Resource (\"*\"). "
            "Rewrite the policy JSON with least-privilege permissions appropriate for a "
            "typical application deployment role. Keep the same Sid labels.\n\n"
        ),
    },
    "K8S-001": {
        "patch_type": "kubernetes",
        "language": "yaml",
        "user_prefix": (
            "The Kubernetes container spec below uses the ':latest' image tag. "
            "Rewrite it with a pinned semver tag (e.g. ':1.0.0'). "
            "Only change the image field.\n\n"
        ),
    },
    "K8S-002": {
        "patch_type": "kubernetes",
        "language": "yaml",
        "user_prefix": (
            "The Kubernetes container spec below has no resource requests or limits. "
            "Add a 'resources' block with reasonable cpu/memory requests and limits "
            "for a typical web workload.\n\n"
        ),
    },
    "K8S-003": {
        "patch_type": "kubernetes",
        "language": "yaml",
        "user_prefix": (
            "The Kubernetes container spec below has privileged: true. "
            "Rewrite the securityContext to set privileged: false, "
            "runAsNonRoot: true, and drop ALL capabilities.\n\n"
        ),
    },
    "K8S-004": {
        "patch_type": "kubernetes",
        "language": "yaml",
        "user_prefix": (
            "The Kubernetes container spec below is missing readinessProbe or livenessProbe. "
            "Add both probes using an httpGet check on /healthz port 8080 "
            "with appropriate initialDelaySeconds and periodSeconds.\n\n"
        ),
    },
    "K8S-005": {
        "patch_type": "kubernetes",
        "language": "yaml",
        "user_prefix": (
            "The Kubernetes Service spec below uses LoadBalancer or NodePort. "
            "Change the type to ClusterIP and add the annotation "
            "'service.beta.kubernetes.io/aws-load-balancer-internal: \"true\"' "
            "if internal access is still needed.\n\n"
        ),
    },
    "K8S-006": {
        "patch_type": "kubernetes",
        "language": "yaml",
        "user_prefix": (
            "The Kubernetes Ingress below has no TLS block. "
            "Add a tls section referencing a secret named '<host>-tls' "
            "and set the host to the first rule's host value.\n\n"
        ),
    },
    "DATA-001": {
