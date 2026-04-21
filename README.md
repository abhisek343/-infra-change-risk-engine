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

```
POST http://localhost:8000/mcp
GET  http://localhost:8000/mcp   ← discovery info
```

Available tools:

| Tool | Description |
|------|-------------|
| `analyze_infrastructure` | Run full risk analysis on Terraform/K8s artifacts |
| `list_policy_rules` | Enumerate all 9 deterministic policy rules |
| `generate_fixes` | LLM-generate corrective patches for a violation list |

Example MCP call:

```bash
curl -X POST http://localhost:8000/mcp \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0", "id": 1,
    "method": "tools/call",
    "params": {
      "name": "analyze_infrastructure",
      "arguments": {
        "environment": "prod",
        "terraform_plan": "<json>",
        "kubernetes_manifest": "<yaml>"
      }
    }
  }'
```

## Local development

### 1. Backend

```bash
cd backend
python3 -m pip install -e '.[dev]'
OPENAI_API_KEY=sk-... uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Worker

Open a second terminal:

```bash
cd backend
OPENAI_API_KEY=sk-... python3 -m app.workers.loop
```

### 3. Frontend

Open a third terminal:

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1 npm run dev
```

Then open:

- Frontend: `http://localhost:3000`
- Backend docs: `http://localhost:8000/docs`
- MCP server: `http://localhost:8000/mcp`

## Docker Compose

```bash
OPENAI_API_KEY=sk-... docker compose up --build
```

To use a local model (Ollama, etc.):

```bash
OPENAI_BASE_URL=http://host.docker.internal:11434/v1 \
  LLM_MODEL=llama3.2 \
  docker compose up --build
```

This starts:

- frontend on `3000`
- backend on `8000`
- worker as a separate service

## Demo flow

1. Start backend + worker + frontend
2. Open the dashboard
3. Load a sample rollout
4. Run analysis
5. Review:
   - decision score
   - blast radius
   - cost delta
   - violations
   - score breakdown
   - recommendations
   - approval history
   - graph preview
6. Click **Generate AI fixes** (or wait for the worker to auto-generate them)
7. Expand each patch to see the corrected Terraform HCL or Kubernetes YAML
8. Open the **Agent Gateway** panel to connect your AI agent via MCP
9. Export the markdown report

## Project structure

```text
infra-change-risk-engine/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   └── fix_agent.py        ← LLM fix-generation agent
│   │   ├── mcp/
│   │   │   ├── tools.py            ← MCP tool definitions
│   │   │   └── server.py           ← JSON-RPC 2.0 MCP HTTP server
│   │   ├── api/routes.py
│   │   ├── services/               ← deterministic analysis pipeline
│   │   └── workers/loop.py         ← auto-triggers fix agent on completion
│   └── pyproject.toml
├── frontend/
├── samples/
│   ├── terraform/
│   └── k8s/
└── docker-compose.yml
```


## What it does

- parses Terraform `resource_changes`
- parses Kubernetes manifest YAML
- normalizes changes into internal resource models
- computes dependency and blast-radius graph data
- evaluates security and platform guardrails
- estimates rough monthly cost delta
- scores deployment risk and returns `APPROVE`, `WARN`, `MANUAL_REVIEW`, or `BLOCK`
- runs analysis through a separate worker process
- keeps approval history per report
- exposes dashboard summaries and recent job history
- exports a shareable markdown report

## Stack

- **Frontend:** Next.js + TypeScript
- **Backend:** FastAPI + SQLAlchemy
- **Persistence:** SQLite
- **Execution:** separate polling worker process
- **Samples:** built-in risky and safe rollouts
- **Workflow:** dashboard, create-analysis flow, report detail view, approval trail

## Local development

### 1. Backend

```bash
cd backend
python3 -m pip install -e '.[dev]'
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Worker

Open a second terminal:

```bash
cd backend
python3 -m app.workers.loop
```

### 3. Frontend

Open a third terminal:

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1 npm run dev
```

Then open:

- Frontend: `http://localhost:3000`
- Backend docs: `http://localhost:8000/docs`

## Docker Compose

```bash
docker compose up --build
```

This starts:

- frontend on `3000`
- backend on `8000`
- worker as a separate service

## Demo flow

1. Start backend + worker + frontend
2. Open the dashboard
3. Load a sample rollout
4. Run analysis
5. Review:
   - decision score
   - blast radius
   - cost delta
   - violations
   - score breakdown
   - recommendations
   - approval history
   - graph preview
6. Export the markdown report

