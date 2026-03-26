"""Tests for MCPAgentSDK main class: init, run_agent, shutdown."""

import asyncio
import json
from unittest.mock import AsyncMock, patch

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


@pytest.mark.asyncio
async def test_timeout_triggers_block():
    """timeout should set status to blocked and call on_block."""
    sdk = MCPAgentSDK()
    await sdk.init(port=0)

    block_reasons: list[str] = []

    def on_block(reason: str) -> None:
        block_reasons.append(reason)

    config = AgentRunConfig(
        prompt="do something slow",
        on_block=on_block,
        timeout=1.0,
    )

    # Mock subprocess: emits one message then blocks (simulates slow agent)
    async def _fake_start_cli_process(cli_path, args, full_prompt, cwd=None):
        proc = AsyncMock()
        proc.returncode = None
        sent_init = False

        class FakeStdout:
            async def readline(self_stdout):
                nonlocal sent_init
                if not sent_init:
                    sent_init = True
                    msg = json.dumps({"type": "system", "subtype": "init", "session_id": "s1"})
                    return (msg + "\n").encode()
                # Block indefinitely — simulates agent doing slow work
                await asyncio.sleep(3600)
                return b""

        proc.stdout = FakeStdout()

        def _terminate():
            proc.returncode = -1

        proc.terminate = _terminate
        proc.kill = lambda: None
        proc.wait = AsyncMock(return_value=-1)
        return proc

    try:
        with (
            patch("mcp_agent_sdk.sdk.find_codebuddy_cli", return_value="codebuddy"),
            patch("mcp_agent_sdk.sdk.start_cli_process", side_effect=_fake_start_cli_process),
        ):
            messages = []
            async for msg in sdk.run_agent(config):
                messages.append(msg)

        final = messages[-1]
        assert final.type == "agent_result"
        assert final.content["status"] == "blocked"
        assert "timed out" in final.content["message"]
        assert len(block_reasons) == 1
        assert "timed out" in block_reasons[0]
    finally:
        await sdk.shutdown()
