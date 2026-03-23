"""Streamable HTTP MCP Server implementation (JSON-RPC 2.0)."""

from __future__ import annotations

import asyncio
import inspect
import json
from typing import Any

from aiohttp import web

from mcp_agent_sdk.types import RunContext

PROTOCOL_VERSION = "2025-03-26"

SERVER_INFO = {
    "name": "agent-controller",
    "version": "0.1.0",
}

TOOLS = [
    {
        "name": "Complete",
        "description": "Mark the task as completed and submit the result for validation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_run_id": {"type": "string", "description": "The agent run ID"},
                "result": {"type": "string", "description": "Task result description"},
            },
            "required": ["agent_run_id", "result"],
        },
    },
    {
        "name": "Block",
        "description": "Mark the task as blocked, requiring human intervention.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_run_id": {"type": "string", "description": "The agent run ID"},
                "reason": {"type": "string", "description": "Reason for being blocked"},
            },
            "required": ["agent_run_id", "reason"],
        },
    },
]


def _jsonrpc_error(id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": id}


def _jsonrpc_result(id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "result": result, "id": id}


async def _call_fn(fn: Any, *args: Any) -> Any:
    """Call a function, awaiting it if it's async."""
    if fn is None:
        return None
    if inspect.iscoroutinefunction(fn):
        return await fn(*args)
    return fn(*args)


async def _safe_call(fn: Any, *args: Any) -> None:
    """Call a callback function, suppressing any exceptions."""
    try:
        await _call_fn(fn, *args)
    except Exception:
        pass


def _handle_initialize(params: dict, id: Any) -> dict:
    return _jsonrpc_result(id, {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {"tools": {}},
        "serverInfo": SERVER_INFO,
    })


def _handle_tools_list(params: dict, id: Any) -> dict:
    return _jsonrpc_result(id, {"tools": TOOLS})


async def _handle_tools_call(params: dict, id: Any, registry: dict[str, RunContext]) -> dict:
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})
    agent_run_id = arguments.get("agent_run_id", "")

    ctx = registry.get(agent_run_id)
    if ctx is None:
        return _jsonrpc_result(id, {
            "content": [{"type": "text", "text": f"Error: unknown agent_run_id '{agent_run_id}'"}],
            "isError": True,
        })

    if tool_name == "Complete":
        return await _handle_complete(ctx, arguments, id)
    elif tool_name == "Block":
        return await _handle_block(ctx, arguments, id)
    else:
        return _jsonrpc_result(id, {
            "content": [{"type": "text", "text": f"Error: unknown tool '{tool_name}'"}],
            "isError": True,
        })


async def _handle_complete(ctx: RunContext, arguments: dict, id: Any) -> dict:
    result_text = arguments.get("result", "")

    if ctx.validate_fn is None:
        ctx.status = "completed"
        ctx.result_message = result_text
        await _safe_call(ctx.on_complete, result_text)
        return _jsonrpc_result(id, {
            "content": [{"type": "text", "text": "Task validated successfully."}],
        })

    try:
        result = await _call_fn(ctx.validate_fn, result_text)
        passed, message = result
    except Exception as exc:
        return _jsonrpc_result(id, {
            "content": [{"type": "text", "text": f"Validation error: {exc}"}],
            "isError": True,
        })

    if passed:
        ctx.status = "completed"
        ctx.result_message = result_text
        await _safe_call(ctx.on_complete, result_text)
        return _jsonrpc_result(id, {
            "content": [{"type": "text", "text": "Task validated successfully."}],
        })
    else:
        ctx.retry_count += 1
        if ctx.retry_count >= ctx.max_retries:
            ctx.status = "blocked"
            ctx.result_message = "Validation retry limit exceeded"
            await _safe_call(ctx.on_block, "Validation retry limit exceeded")
            return _jsonrpc_result(id, {
                "content": [{"type": "text", "text": "Maximum retry count reached. Task is now blocked."}],
            })
        return _jsonrpc_result(id, {
            "content": [{"type": "text", "text": f"Validation failed: {message}. Please fix and try again."}],
        })


async def _handle_block(ctx: RunContext, arguments: dict, id: Any) -> dict:
    reason = arguments.get("reason", "")
    ctx.status = "blocked"
    ctx.result_message = reason
    await _safe_call(ctx.on_block, reason)
    return _jsonrpc_result(id, {
        "content": [{"type": "text", "text": "Task blocked. Reason recorded, task will be paused."}],
    })


async def handle_mcp(request: web.Request) -> web.Response:
    """Handle incoming JSON-RPC 2.0 requests on POST /mcp."""
    registry: dict[str, RunContext] = request.app["registry"]

    try:
        body = await request.json()
    except (json.JSONDecodeError, Exception):
        return web.json_response(
            _jsonrpc_error(None, -32700, "Parse error")
        )

    # Validate basic JSON-RPC structure
    if not isinstance(body, dict) or body.get("jsonrpc") != "2.0":
        return web.json_response(
            _jsonrpc_error(body.get("id") if isinstance(body, dict) else None, -32600, "Invalid Request")
        )

    method = body.get("method", "")
    params = body.get("params", {})
    msg_id = body.get("id")

    # Notifications (no id) - process but don't return meaningful result
    if msg_id is None:
        if method == "notifications/initialized":
            return web.json_response({})
        return web.json_response({})

    # Route to handler
    if method == "initialize":
        return web.json_response(_handle_initialize(params, msg_id))
    elif method == "tools/list":
        return web.json_response(_handle_tools_list(params, msg_id))
    elif method == "tools/call":
        return web.json_response(await _handle_tools_call(params, msg_id, registry))
    else:
        return web.json_response(_jsonrpc_error(msg_id, -32601, "Method not found"))


def create_mcp_app(registry: dict[str, RunContext]) -> web.Application:
    """Create an aiohttp Application with the MCP endpoint."""
    app = web.Application()
    app["registry"] = registry
    app.router.add_post("/mcp", handle_mcp)
    return app
