# Infra Change Risk Engine

An infrastructure pre-deploy gate that turns Terraform and Kubernetes changes into explainable risk decisions, approval evidence, and optional corrective patches.

The project separates deterministic policy evaluation from LLM-assisted remediation: the policy engine decides whether a change is safe enough to proceed, while the LLM can suggest fixes for human review.

## What it does

- Parses Terraform `resource_changes` and Kubernetes manifest YAML.
- Normalizes changes into resource and dependency models.
- Evaluates nine deterministic security and platform guardrails.
- Computes dependency, blast-radius, and rough monthly cost signals.
- Produces one of `APPROVE`, `WARN`, `MANUAL_REVIEW`, or `BLOCK`.
- Stores approval history and exports shareable Markdown reports.
- Runs analysis through a separate worker process.
- Exposes an MCP server so compatible agents can invoke analysis.
- Optionally generates corrected Terraform or Kubernetes patches for detected violations.

The deterministic policy result remains authoritative. LLM output is optional advisory material and never overrides a policy decision.

## Example policies

| Rule | Example remediation |
|---|---|
| `NET-001` | Replace `0.0.0.0/0` with a VPC-scoped CIDR or security-group reference |
| `IAM-001` | Replace wildcard permissions with least-privilege actions |
| `K8S-001` | Pin an image tag instead of using `:latest` |
| `K8S-002` | Add CPU and memory requests and limits |
| `K8S-003` | Drop privileges and set `runAsNonRoot` |
| `K8S-004` | Add readiness and liveness probes |

## Stack

- **Frontend:** Next.js, TypeScript
- **Backend:** FastAPI, SQLAlchemy
- **Persistence:** SQLite
- **Execution:** separate polling worker
- **Agent protocol:** MCP over JSON-RPC 2.0
- **LLM:** any OpenAI-compatible endpoint, optional
- **Samples:** safe and intentionally risky rollout fixtures

## Local demo

Start the stack:

```bash
docker compose up --build
```

Open the dashboard at [http://localhost:3000](http://localhost:3000), load a sample rollout, and run an analysis. The report exposes:

- the final risk decision and score breakdown
- violated policies and recommendations
- dependency and blast-radius information
- estimated cost delta
- approval history
- generated Terraform or Kubernetes patches, when an LLM endpoint is configured

No API key is required for deterministic analysis. To enable optional patch generation, configure the endpoint through environment variables rather than committing credentials:

```bash
OPENAI_BASE_URL=http://localhost:11434/v1 \
LLM_MODEL=llama3.2 \
docker compose up --build
```

## MCP interface

The local server exposes:

```text
POST http://localhost:8000/mcp
GET  http://localhost:8000/mcp
```

Available tools include:

- `analyze_infrastructure`
- `list_policy_rules`
- `generate_fixes`

Example request:

```bash
curl -X POST http://localhost:8000/mcp \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
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

## Development

### Backend

```bash
cd backend
python3 -m pip install -e '.[dev]'
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Worker

In a second terminal:

```bash
cd backend
python3 -m app.workers.loop
```

### Frontend

In a third terminal:

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1 npm run dev
```

## Project structure

```text
backend/
├── app/
│   ├── agents/       # optional patch-generation agent
│   ├── api/          # HTTP API routes
│   ├── mcp/          # MCP JSON-RPC server and tools
│   ├── services/     # deterministic analysis pipeline
│   └── workers/      # background analysis worker
frontend/             # dashboard
samples/              # safe and risky Terraform/Kubernetes inputs
docker-compose.yml
```

## Safety and scope

This is a local reference implementation for evaluating infrastructure changes. Review every generated patch before applying it. Keep credentials in an untracked environment file or secret manager, and never commit `OPENAI_API_KEY` or other provider credentials.

## License

See [LICENSE](LICENSE).
