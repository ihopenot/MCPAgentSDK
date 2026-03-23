"""Tests for MCPAgentSDK main class: init, run_agent, shutdown."""

import asyncio
import json

import pytest
import pytest_asyncio
from aiohttp import ClientSession

from mcp_agent_sdk.sdk import MCPAgentSDK
from mcp_agent_sdk.types import AgentRunConfig, Message


@pytest.mark.asyncio
async def test_init_starts_server():
    """init() should start the MCP server on an available port."""
    sdk = MCPAgentSDK()
    await sdk.init(port=0)
    try:
        assert sdk.port > 0
        # Server should respond to POST /mcp
        async with ClientSession() as session:
            resp = await session.post(
                f"http://127.0.0.1:{sdk.port}/mcp",
                json={"jsonrpc": "2.0", "method": "initialize", "id": 1, "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0"},
                }},
            )
            data = await resp.json()
            assert data["result"]["serverInfo"]["name"] == "agent-controller"
    finally:
        await sdk.shutdown()


@pytest.mark.asyncio
async def test_shutdown_stops_server():
    """shutdown() should stop the server and clean up."""
    sdk = MCPAgentSDK()
    await sdk.init(port=0)
    port = sdk.port
    await sdk.shutdown()

    # Server should no longer respond
    async with ClientSession() as session:
        with pytest.raises(Exception):
            await session.post(
                f"http://127.0.0.1:{port}/mcp",
                json={"jsonrpc": "2.0", "method": "initialize", "id": 1, "params": {}},
            )


@pytest.mark.asyncio
async def test_init_without_shutdown_is_safe():
    """Multiple init calls should work (idempotent)."""
    sdk = MCPAgentSDK()
    await sdk.init(port=0)
    port1 = sdk.port
    await sdk.shutdown()
    await sdk.init(port=0)
    port2 = sdk.port
    await sdk.shutdown()
    # Both should have been valid ports
    assert port1 > 0
    assert port2 > 0


@pytest.mark.asyncio
async def test_registry_is_empty_after_init():
    """Registry should be empty after init."""
    sdk = MCPAgentSDK()
    await sdk.init(port=0)
    try:
        assert len(sdk._registry) == 0
    finally:
        await sdk.shutdown()


@pytest.mark.asyncio
async def test_mcp_server_url_property():
    """mcp_server_url should return the correct URL."""
    sdk = MCPAgentSDK()
    await sdk.init(host="127.0.0.1", port=0)
    try:
        url = sdk.mcp_server_url
        assert url.startswith("http://127.0.0.1:")
        assert url.endswith("/mcp")
    finally:
        await sdk.shutdown()
