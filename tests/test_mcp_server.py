"""Tests for MCP Server: JSON-RPC 2.0, initialize, tools/list, tools/call."""

import asyncio
import json

import pytest
import pytest_asyncio
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, TestClient, TestServer

from mcp_agent_sdk.mcp_server import create_mcp_app
from mcp_agent_sdk.types import RunContext


@pytest_asyncio.fixture
async def mcp_client(aiohttp_client):
    """Create a test client for the MCP server with empty registry."""
    registry = {}
    app = create_mcp_app(registry)
    client = await aiohttp_client(app)
    return client


def _make_registry_with_context(**kwargs) -> tuple[dict, str, RunContext]:
    """Helper to create a registry with one RunContext."""
    ctx = RunContext(**kwargs)
    agent_run_id = "test-run-123"
    registry = {agent_run_id: ctx}
    return registry, agent_run_id, ctx


@pytest_asyncio.fixture
async def mcp_client_with_ctx(aiohttp_client):
    """Create a test client with a registered agent run (validate always passes)."""
    registry, agent_run_id, ctx = _make_registry_with_context(
        validate_fn=lambda r: (True, ""),
        on_complete=None,
        on_block=None,
        max_retries=3,
    )
    app = create_mcp_app(registry)
    client = await aiohttp_client(app)
    return client, registry, agent_run_id, ctx


async def _post_jsonrpc(client, method: str, params: dict | None = None, id: int = 1):
    """Helper to send a JSON-RPC 2.0 request."""
    payload = {"jsonrpc": "2.0", "method": method, "id": id}
    if params is not None:
        payload["params"] = params
    resp = await client.post("/mcp", json=payload)
    assert resp.status == 200
    return await resp.json()


@pytest.mark.asyncio
async def test_initialize(mcp_client):
    """initialize should return server info and capabilities."""
    result = await _post_jsonrpc(mcp_client, "initialize", {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1.0"}
    })
    assert "result" in result
    assert result["result"]["protocolVersion"] == "2025-03-26"
    assert "serverInfo" in result["result"]
    assert result["result"]["serverInfo"]["name"] == "agent-controller"
    assert "tools" in result["result"]["capabilities"]


@pytest.mark.asyncio
async def test_tools_list(mcp_client):
    """tools/list should return Complete and Block tool definitions."""
    # Must initialize first
    await _post_jsonrpc(mcp_client, "initialize", {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1.0"}
    })
    result = await _post_jsonrpc(mcp_client, "tools/list", {}, id=2)
    assert "result" in result
    tools = result["result"]["tools"]
    assert len(tools) == 2
    tool_names = {t["name"] for t in tools}
    assert tool_names == {"Complete", "Block"}

    # Verify Complete tool schema
    complete_tool = next(t for t in tools if t["name"] == "Complete")
    assert "agent_run_id" in complete_tool["inputSchema"]["properties"]
    assert "result" in complete_tool["inputSchema"]["properties"]
    assert set(complete_tool["inputSchema"]["required"]) == {"agent_run_id", "result"}

    # Verify Block tool schema
    block_tool = next(t for t in tools if t["name"] == "Block")
    assert "agent_run_id" in block_tool["inputSchema"]["properties"]
    assert "reason" in block_tool["inputSchema"]["properties"]
    assert set(block_tool["inputSchema"]["required"]) == {"agent_run_id", "reason"}


@pytest.mark.asyncio
async def test_invalid_jsonrpc(mcp_client):
    """Invalid JSON-RPC should return an error response."""
    resp = await mcp_client.post("/mcp", json={"invalid": True})
    assert resp.status == 200
    data = await resp.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_unknown_method(mcp_client):
    """Unknown method should return method not found error."""
    result = await _post_jsonrpc(mcp_client, "nonexistent/method")
    assert "error" in result
    assert result["error"]["code"] == -32601  # Method not found


@pytest.mark.asyncio
async def test_notifications_initialized(mcp_client):
    """notifications/initialized should return empty success."""
    # This is a notification (no response expected), but we send with id
    payload = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    resp = await mcp_client.post("/mcp", json=payload)
    assert resp.status == 200


# === tools/call tests ===


@pytest.mark.asyncio
async def test_complete_validation_passes(mcp_client_with_ctx):
    """Complete with passing validate_fn should set status to completed."""
    client, registry, run_id, ctx = mcp_client_with_ctx
    result = await _post_jsonrpc(client, "tools/call", {
        "name": "Complete",
        "arguments": {"agent_run_id": run_id, "result": "task done"},
    })
    assert "result" in result
    assert "validated successfully" in result["result"]["content"][0]["text"].lower()
    assert ctx.status == "completed"
    assert ctx.result_message == "task done"


@pytest.mark.asyncio
async def test_complete_validation_fails_and_retries(aiohttp_client):
    """Complete with failing validate_fn should increment retry_count."""
    registry, run_id, ctx = _make_registry_with_context(
        validate_fn=lambda r: (False, "needs more work"),
        on_complete=None,
        on_block=None,
        max_retries=3,
    )
    app = create_mcp_app(registry)
    client = await aiohttp_client(app)

    result = await _post_jsonrpc(client, "tools/call", {
        "name": "Complete",
        "arguments": {"agent_run_id": run_id, "result": "incomplete"},
    })
    assert "result" in result
    text = result["result"]["content"][0]["text"]
    assert "needs more work" in text
    assert ctx.status == "running"
    assert ctx.retry_count == 1


@pytest.mark.asyncio
async def test_complete_max_retries_triggers_blocked(aiohttp_client):
    """Exceeding max_retries should set status to blocked."""
    registry, run_id, ctx = _make_registry_with_context(
        validate_fn=lambda r: (False, "still wrong"),
        on_complete=None,
        on_block=None,
        max_retries=2,
    )
    app = create_mcp_app(registry)
    client = await aiohttp_client(app)

    # First retry
    await _post_jsonrpc(client, "tools/call", {
        "name": "Complete",
        "arguments": {"agent_run_id": run_id, "result": "attempt 1"},
    })
    assert ctx.retry_count == 1
    assert ctx.status == "running"

    # Second retry - should trigger blocked
    result = await _post_jsonrpc(client, "tools/call", {
        "name": "Complete",
        "arguments": {"agent_run_id": run_id, "result": "attempt 2"},
    })
    assert ctx.status == "blocked"
    assert "retry" in ctx.result_message.lower()


@pytest.mark.asyncio
async def test_complete_no_validate_fn(aiohttp_client):
    """Complete without validate_fn should auto-complete."""
    registry, run_id, ctx = _make_registry_with_context(
        validate_fn=None,
        on_complete=None,
        on_block=None,
        max_retries=3,
    )
    app = create_mcp_app(registry)
    client = await aiohttp_client(app)

    result = await _post_jsonrpc(client, "tools/call", {
        "name": "Complete",
        "arguments": {"agent_run_id": run_id, "result": "done"},
    })
    assert ctx.status == "completed"


@pytest.mark.asyncio
async def test_complete_triggers_on_complete_callback(aiohttp_client):
    """Complete with passing validation should call on_complete."""
    callback_results = []
    registry, run_id, ctx = _make_registry_with_context(
        validate_fn=lambda r: (True, ""),
        on_complete=lambda r: callback_results.append(r),
        on_block=None,
        max_retries=3,
    )
    app = create_mcp_app(registry)
    client = await aiohttp_client(app)

    await _post_jsonrpc(client, "tools/call", {
        "name": "Complete",
        "arguments": {"agent_run_id": run_id, "result": "all good"},
    })
    assert callback_results == ["all good"]


@pytest.mark.asyncio
async def test_block_sets_status_and_reason(aiohttp_client):
    """Block should set status to blocked with the given reason."""
    registry, run_id, ctx = _make_registry_with_context(
        validate_fn=None,
        on_complete=None,
        on_block=None,
        max_retries=3,
    )
    app = create_mcp_app(registry)
    client = await aiohttp_client(app)

    result = await _post_jsonrpc(client, "tools/call", {
        "name": "Block",
        "arguments": {"agent_run_id": run_id, "reason": "need API key"},
    })
    assert "result" in result
    assert ctx.status == "blocked"
    assert ctx.result_message == "need API key"


@pytest.mark.asyncio
async def test_block_triggers_on_block_callback(aiohttp_client):
    """Block should call on_block callback."""
    callback_reasons = []
    registry, run_id, ctx = _make_registry_with_context(
        validate_fn=None,
        on_complete=None,
        on_block=lambda r: callback_reasons.append(r),
        max_retries=3,
    )
    app = create_mcp_app(registry)
    client = await aiohttp_client(app)

    await _post_jsonrpc(client, "tools/call", {
        "name": "Block",
        "arguments": {"agent_run_id": run_id, "reason": "stuck"},
    })
    assert callback_reasons == ["stuck"]


@pytest.mark.asyncio
async def test_unknown_agent_run_id(mcp_client):
    """tools/call with unknown agent_run_id should return error."""
    result = await _post_jsonrpc(mcp_client, "tools/call", {
        "name": "Complete",
        "arguments": {"agent_run_id": "nonexistent", "result": "done"},
    })
    assert result["result"]["isError"] is True
    assert "unknown" in result["result"]["content"][0]["text"].lower()


@pytest.mark.asyncio
async def test_unknown_tool_name(mcp_client_with_ctx):
    """tools/call with unknown tool name should return error."""
    client, registry, run_id, ctx = mcp_client_with_ctx
    result = await _post_jsonrpc(client, "tools/call", {
        "name": "UnknownTool",
        "arguments": {"agent_run_id": run_id},
    })
    assert result["result"]["isError"] is True


@pytest.mark.asyncio
async def test_complete_max_retries_triggers_on_block_callback(aiohttp_client):
    """Exceeding max_retries should fire on_block callback."""
    callback_reasons = []
    registry, run_id, ctx = _make_registry_with_context(
        validate_fn=lambda r: (False, "nope"),
        on_complete=None,
        on_block=lambda r: callback_reasons.append(r),
        max_retries=1,
    )
    app = create_mcp_app(registry)
    client = await aiohttp_client(app)

    await _post_jsonrpc(client, "tools/call", {
        "name": "Complete",
        "arguments": {"agent_run_id": run_id, "result": "attempt"},
    })
    assert ctx.status == "blocked"
    assert callback_reasons == ["Validation retry limit exceeded"]


@pytest.mark.asyncio
async def test_concurrent_agents_isolated(aiohttp_client):
    """Two agents with different run IDs should not interfere."""
    ctx_a = RunContext(validate_fn=lambda r: (True, ""), on_complete=None, on_block=None, max_retries=3)
    ctx_b = RunContext(validate_fn=lambda r: (False, "fail"), on_complete=None, on_block=None, max_retries=3)
    registry = {"run-a": ctx_a, "run-b": ctx_b}
    app = create_mcp_app(registry)
    client = await aiohttp_client(app)

    await _post_jsonrpc(client, "tools/call", {
        "name": "Complete",
        "arguments": {"agent_run_id": "run-a", "result": "done"},
    })
    await _post_jsonrpc(client, "tools/call", {
        "name": "Complete",
        "arguments": {"agent_run_id": "run-b", "result": "done"},
    })
    assert ctx_a.status == "completed"
    assert ctx_b.status == "running"  # failed validation, still running
    assert ctx_b.retry_count == 1


@pytest.mark.asyncio
async def test_async_validate_fn(aiohttp_client):
    """Async validate_fn should be awaited correctly."""
    async def async_validator(result: str) -> tuple[bool, str]:
        await asyncio.sleep(0)
        return (True, "")

    registry, run_id, ctx = _make_registry_with_context(
        validate_fn=async_validator,
        on_complete=None,
        on_block=None,
        max_retries=3,
    )
    app = create_mcp_app(registry)
    client = await aiohttp_client(app)

    await _post_jsonrpc(client, "tools/call", {
        "name": "Complete",
        "arguments": {"agent_run_id": run_id, "result": "done"},
    })
    assert ctx.status == "completed"


@pytest.mark.asyncio
async def test_async_on_complete_callback(aiohttp_client):
    """Async on_complete callback should be awaited correctly."""
    callback_results = []

    async def async_on_complete(result: str):
        await asyncio.sleep(0)
        callback_results.append(result)

    registry, run_id, ctx = _make_registry_with_context(
        validate_fn=lambda r: (True, ""),
        on_complete=async_on_complete,
        on_block=None,
        max_retries=3,
    )
    app = create_mcp_app(registry)
    client = await aiohttp_client(app)

    await _post_jsonrpc(client, "tools/call", {
        "name": "Complete",
        "arguments": {"agent_run_id": run_id, "result": "async done"},
    })
    assert callback_results == ["async done"]
