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
        "patch_type": "advisory",
        "language": "text",
        "user_prefix": (
            "A production database instance is being modified. "
            "Generate a YAML-formatted pre-flight checklist (as plain YAML, "
            "not wrapped in a Kubernetes manifest) that a DBA must complete "
            "before this Terraform apply is allowed to proceed.\n\n"
        ),
    },
}

_FALLBACK_ADVISORY = (
    "LLM fix generation is not configured (OPENAI_API_KEY not set). "
    "Set the environment variable and re-run the analysis to receive "
    "an auto-generated corrective patch for this violation."
)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def generate_fixes(
    violations: list[dict[str, Any]],
    terraform_plan: str | None,
    kubernetes_manifest: str | None,
) -> list[dict[str, Any]]:
    """
    For each violation produce a FixPatch dict.  Calls the LLM when an API key
    is available; returns advisory-only patches otherwise so the rest of the
    pipeline always has structured output.
    """
    patches: list[dict[str, Any]] = []

    for violation in violations:
        code: str = violation.get("code", "UNKNOWN")
        title: str = violation.get("title", code)
        ctx = _VIOLATION_CONTEXT.get(code)

        if ctx is None:
            patches.append(_advisory_patch(code, title, f"No fix template available for {code}."))
            continue

        artifact_snippet = _extract_snippet(code, violation, terraform_plan, kubernetes_manifest)
        patch_content, explanation, model_used = _call_llm(ctx, artifact_snippet)

        patches.append({
            "violation_code": code,
            "violation_title": title,
            "patch_type": ctx["patch_type"],
            "language": ctx["language"],
            "patch_content": patch_content,
            "explanation": explanation,
            "llm_model": model_used,
        })

    return patches


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _call_llm(ctx: dict[str, str], snippet: str) -> tuple[str, str, str]:
    """Call the LLM and return (patch_content, explanation, model_used)."""
    if not LLM_API_KEY:
        return _FALLBACK_ADVISORY, "Set OPENAI_API_KEY to enable automatic fix generation.", ""

    try:
        from openai import OpenAI  # imported lazily so the module loads without the package

        client_kwargs: dict[str, Any] = {"api_key": LLM_API_KEY}
        if LLM_BASE_URL:
            client_kwargs["base_url"] = LLM_BASE_URL

        client = OpenAI(**client_kwargs)
        user_message = ctx["user_prefix"] + (snippet or "(no artifact snippet available)")

        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.15,
            max_tokens=800,
        )

        raw = (response.choices[0].message.content or "").strip()
        parsed = json.loads(raw)
        return str(parsed.get("patch_content", raw)), str(parsed.get("explanation", "")), LLM_MODEL

    except json.JSONDecodeError:
        return raw, "LLM returned unstructured content.", LLM_MODEL  # type: ignore[possibly-undefined]
    except Exception as exc:  # noqa: BLE001
        log.warning("LLM fix generation failed for %s: %s", ctx.get("patch_type"), exc)
        return (
            f"# Fix generation failed: {exc}",
            "An error occurred while calling the LLM.",
            LLM_MODEL,
        )


def _extract_snippet(
    code: str,
    violation: dict[str, Any],
    terraform_plan: str | None,
    kubernetes_manifest: str | None,
) -> str:
    """Pull a small relevant snippet from the artifacts for the LLM prompt."""
    evidence = violation.get("evidence", {})
    resource_id: str = str(evidence.get("resource", ""))

    if code.startswith("K8S-") and kubernetes_manifest:
        return _k8s_snippet(kubernetes_manifest, resource_id)

    if terraform_plan:
        return _tf_snippet(terraform_plan, resource_id)

    return ""


def _tf_snippet(terraform_plan: str, resource_id: str) -> str:
    try:
        plan = json.loads(terraform_plan)
        for change in plan.get("resource_changes", []):
            addr = change.get("address", "")
            if addr == resource_id or resource_id in addr:
                after = change.get("change", {}).get("after") or {}
                return json.dumps(after, indent=2)[:1500]
    except Exception:  # noqa: BLE001
        pass
    return terraform_plan[:1000] if terraform_plan else ""


def _k8s_snippet(manifest: str, resource_id: str) -> str:
    """Return the YAML text for the matching document (matched by name/namespace)."""
    try:
        import yaml

        parts = resource_id.split("/")
        target_name = parts[-1] if parts else ""
        docs = list(yaml.safe_load_all(manifest))
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            meta = doc.get("metadata") or {}
            if meta.get("name") == target_name or not target_name:
                return yaml.dump(doc, default_flow_style=False)[:1500]
    except Exception:  # noqa: BLE001
        pass
    return manifest[:1000] if manifest else ""


def _advisory_patch(code: str, title: str, message: str) -> dict[str, Any]:
    return {
        "violation_code": code,
        "violation_title": title,
        "patch_type": "advisory",
        "language": "text",
        "patch_content": message,
        "explanation": message,
        "llm_model": "",
    }
