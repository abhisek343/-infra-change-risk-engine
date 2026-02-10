# Infra Change Risk Engine

An AI-augmented infrastructure pre-deploy gate: **deterministic policy engine** + **LLM fix-generation agent** + **MCP tool server**. Agents can invoke the risk analysis natively; violations auto-generate corrected Terraform/K8s patches.

## What it does

- parses Terraform `resource_changes` and Kubernetes manifest YAML
- normalizes changes into internal resource models
- computes dependency and blast-radius graph data
- evaluates security and platform guardrails (9 deterministic rules)
- estimates rough monthly cost delta
- scores deployment risk → `APPROVE`, `WARN`, `MANUAL_REVIEW`, or `BLOCK`
- **auto-generates LLM fix patches** for every violation (corrected HCL / YAML diffs)
- **exposes an MCP tool server** at `/mcp` so AI agents can invoke analysis natively
- runs analysis through a separate worker process
- keeps approval history per report
- exposes dashboard summaries and recent job history
- exports a shareable markdown report

## Stack

- **Frontend:** Next.js + TypeScript
- **Backend:** FastAPI + SQLAlchemy
- **Persistence:** SQLite
- **Execution:** separate polling worker process
- **LLM:** OpenAI-compatible API (GPT-4o-mini by default; swap via env vars)
- **Agent protocol:** Model Context Protocol (MCP) — JSON-RPC 2.0 over HTTP
- **Samples:** built-in risky and safe rollouts
- **Workflow:** dashboard, create-analysis flow, report detail view, approval trail

## AI features

### LLM fix-generation agent

When the deterministic engine finds violations, the worker automatically calls an OpenAI-compatible LLM to produce a corrective patch for each one:

| Violation | Patch type | What the agent fixes |
|-----------|-----------|----------------------|
| NET-001 | Terraform HCL | Replaces `0.0.0.0/0` cidr with VPC-scoped CIDR or SG ref |
| IAM-001 | Terraform JSON | Rewrites wildcard policy to least-privilege |
| K8S-001 | Kubernetes YAML | Pins `:latest` to a semver tag |
| K8S-002 | Kubernetes YAML | Adds `resources` requests and limits |
| K8S-003 | Kubernetes YAML | Drops privileges, sets `runAsNonRoot` |
| K8S-004 | Kubernetes YAML | Adds `readinessProbe` and `livenessProbe` |
| K8S-005 | Kubernetes YAML | Switches Service to ClusterIP |
| K8S-006 | Kubernetes YAML | Adds TLS block to Ingress |
| DATA-001 | Advisory text | Generates DBA pre-flight checklist |

Set `OPENAI_API_KEY` to enable live patches. Without it, advisory-only text is returned — no other functionality is affected.

### MCP tool server

AI agents (Claude Desktop, LLM CI pipelines, custom agents) can point their MCP client at:

