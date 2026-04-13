"""
MCP (Model Context Protocol) HTTP server.

Implements JSON-RPC 2.0 over HTTP POST at /mcp, following the MCP spec
(https://modelcontextprotocol.io/specification). AI agents — Claude Desktop,
custom LLM loops, CI pipelines — can point their MCP client at this endpoint
to natively invoke the Infra Change Risk Engine's analysis and fix tools.

Supported methods
-----------------
initialize          Protocol handshake; returns server capabilities.
tools/list          Returns the tool catalogue.
tools/call          Invokes one of the three registered tools.

Usage from an MCP client
------------------------
    POST http://localhost:8000/mcp
    Content-Type: application/json

    {"jsonrpc":"2.0","id":1,"method":"tools/call",
     "params":{"name":"analyze_infrastructure",
               "arguments":{"environment":"prod","terraform_plan":"..."}}}
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.agents.fix_agent import generate_fixes
from app.mcp.tools import POLICY_RULES, TOOLS
from app.services.analyzer import run_analysis

router = APIRouter()

_SERVER_INFO = {"name": "infra-risk-mcp-server", "version": "0.2.0"}
_PROTOCOL_VERSION = "2024-11-05"


# ---------------------------------------------------------------------------
# JSON-RPC helpers
# ---------------------------------------------------------------------------

def _ok(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _err(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _text_content(text: str) -> list[dict[str, str]]:
    return [{"type": "text", "text": text}]


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

def _handle_analyze_infrastructure(args: dict[str, Any]) -> dict[str, Any]:
    environment = str(args.get("environment", "staging"))
    terraform_plan = args.get("terraform_plan") or None
    kubernetes_manifest = args.get("kubernetes_manifest") or None

    if not terraform_plan and not kubernetes_manifest:
        raise ValueError("Provide at least one of terraform_plan or kubernetes_manifest.")

    report = run_analysis(environment, terraform_plan, kubernetes_manifest)

    # Auto-attach LLM fix patches when violations are present
    violations = report.get("violations", [])
    if violations:
        patches = generate_fixes(violations, terraform_plan, kubernetes_manifest)
        report["fix_patches"] = patches

    return {"content": _text_content(json.dumps(report, indent=2))}


def _handle_list_policy_rules(_args: dict[str, Any]) -> dict[str, Any]:
    return {"content": _text_content(json.dumps(POLICY_RULES, indent=2))}


def _handle_generate_fixes(args: dict[str, Any]) -> dict[str, Any]:
    violations = args.get("violations") or []
    if not isinstance(violations, list):
        raise ValueError("'violations' must be an array.")
    terraform_plan = args.get("terraform_plan") or None
    kubernetes_manifest = args.get("kubernetes_manifest") or None

    patches = generate_fixes(violations, terraform_plan, kubernetes_manifest)
    return {"content": _text_content(json.dumps(patches, indent=2))}


_TOOL_HANDLERS = {
    "analyze_infrastructure": _handle_analyze_infrastructure,
    "list_policy_rules": _handle_list_policy_rules,
    "generate_fixes": _handle_generate_fixes,
}


# ---------------------------------------------------------------------------
# JSON-RPC dispatcher
# ---------------------------------------------------------------------------

def _dispatch(method: str, params: dict[str, Any], request_id: Any) -> dict[str, Any]:
    if method == "initialize":
        return _ok(request_id, {
            "protocolVersion": _PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": _SERVER_INFO,
        })

    if method == "tools/list":
        return _ok(request_id, {"tools": TOOLS})

    if method == "tools/call":
        name: str = params.get("name", "")
        arguments: dict[str, Any] = params.get("arguments") or {}
        handler = _TOOL_HANDLERS.get(name)
        if handler is None:
            return _err(request_id, -32601, f"Unknown tool: {name!r}")
        try:
            result = handler(arguments)
            return _ok(request_id, result)
        except ValueError as exc:
            return _err(request_id, -32602, str(exc))
        except Exception as exc:  # noqa: BLE001
            return _err(request_id, -32603, f"Tool execution error: {exc}")

    if method == "notifications/initialized":
        # Client acknowledgement — no response needed per spec, but return empty ok
        return _ok(request_id, {})

    return _err(request_id, -32601, f"Method not found: {method!r}")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("")
async def mcp_rpc(request: Request) -> JSONResponse:
    """JSON-RPC 2.0 endpoint — handles all MCP method calls."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(_err(None, -32700, "Parse error: invalid JSON"), status_code=400)

    request_id = body.get("id")
    method: str = body.get("method", "")
    params: dict[str, Any] = body.get("params") or {}

    response = _dispatch(method, params, request_id)
    return JSONResponse(response)


@router.get("")
async def mcp_info() -> JSONResponse:
    """Human-readable discovery endpoint — shows server info and tool catalogue."""
    return JSONResponse({
        "server": _SERVER_INFO,
        "protocol_version": _PROTOCOL_VERSION,
        "endpoint": "POST /mcp  (JSON-RPC 2.0)",
        "tools": [{"name": t["name"], "description": t["description"]} for t in TOOLS],
        "usage": {
            "initialize": {"method": "initialize", "params": {"protocolVersion": _PROTOCOL_VERSION, "capabilities": {}, "clientInfo": {"name": "my-agent", "version": "1.0"}}},
            "list_tools": {"method": "tools/list"},
            "call_tool": {"method": "tools/call", "params": {"name": "analyze_infrastructure", "arguments": {"environment": "prod", "terraform_plan": "<json>"}}},
        },
    })
