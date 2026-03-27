"""Tests for sdk.py yielding structured StreamEvent types instead of Message."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_agent_sdk.types import (
    AgentResult,
    AgentRunConfig,
    AssistantMessage,
    StreamEvent,
    SystemMessage,
)


def _make_process_with_complete(stdout_lines, stderr_lines, run_id, mcp_registry):
    """Create a mock process that simulates MCP Complete call via registry."""
    stdout_data = "".join(line + "\n" for line in stdout_lines).encode()
    stderr_data = "".join(line + "\n" for line in stderr_lines).encode()

    process = MagicMock()
    process.returncode = None

    stdout_reader = asyncio.StreamReader()
    stderr_reader = asyncio.StreamReader()

    process.stdout = stdout_reader
    process.stderr = stderr_reader

    process.stdin = MagicMock()
    process.stdin.write = MagicMock()
    process.stdin.drain = AsyncMock()
    process.stdin.close = MagicMock()

    async def _wait():
        process.returncode = 0
        return 0

    process.wait = _wait
    process.terminate = MagicMock()
    process.kill = MagicMock()

    # Feed data and simulate Complete via registry after messages are consumed
    async def _feed():
        for line in stdout_lines:
            stdout_reader.feed_data((line + "\n").encode())
            await asyncio.sleep(0.01)
        # Give SDK time to read and process all lines before status change
        await asyncio.sleep(0.5)
        # Simulate agent calling Complete via MCP
        if run_id and run_id in mcp_registry:
            ctx = mcp_registry[run_id]
            ctx.status = "completed"
            ctx.result_message = "task done"
        await asyncio.sleep(0.1)
        stdout_reader.feed_eof()

    stderr_reader.feed_data(stderr_data)
    stderr_reader.feed_eof()

    return process, _feed


class TestRunAgentYieldsStructuredTypes:
    """run_agent() should yield StreamEvent subclasses, not Message."""

    @pytest.mark.asyncio
    async def test_yields_stream_events(self):
        from mcp_agent_sdk.sdk import MCPAgentSDK

        sdk = MCPAgentSDK()
        await sdk.init()

        try:
            stdout_lines = [
                json.dumps({"type": "system", "subtype": "init", "session_id": "s1"}),
                json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "hi"}]}}),
            ]

            config = AgentRunConfig(prompt="test")

            # We need the run_id to set up the mock — capture it via registry
            original_run_agent = sdk.run_agent

            collected = []

            with patch("mcp_agent_sdk.sdk.find_codebuddy_cli", return_value="/fake/cli"):
                # Intercept start_cli_process to get access to registry
                async def mock_start(cli_path, args, full_prompt, cwd=None):
                    # Find the run_id from the registry
                    run_ids = list(sdk._registry.keys())
                    run_id = run_ids[-1] if run_ids else None
                    process, feed_coro = _make_process_with_complete(
                        stdout_lines, [], run_id, sdk._registry,
                    )
                    asyncio.create_task(feed_coro())
                    return process

                with patch("mcp_agent_sdk.sdk.start_cli_process", side_effect=mock_start):
                    async for event in sdk.run_agent(config):
                        collected.append(event)

            # All yielded items should be StreamEvent instances
            for event in collected:
                assert isinstance(event, StreamEvent), (
                    f"Expected StreamEvent, got {type(event).__name__}: {event}"
                )

            # Should have system message, assistant message, and agent_result
            types_seen = [type(e).__name__ for e in collected]
            assert "SystemMessage" in types_seen
            assert "AssistantMessage" in types_seen
            assert "AgentResult" in types_seen

        finally:
            await sdk.shutdown()

    @pytest.mark.asyncio
    async def test_agent_result_has_correct_fields(self):
        from mcp_agent_sdk.sdk import MCPAgentSDK

        sdk = MCPAgentSDK()
        await sdk.init()

        try:
            stdout_lines = [
                json.dumps({"type": "system", "subtype": "init", "session_id": "sess-test"}),
            ]

            config = AgentRunConfig(prompt="test")
            final_result = None

            with patch("mcp_agent_sdk.sdk.find_codebuddy_cli", return_value="/fake/cli"):
                async def mock_start(cli_path, args, full_prompt, cwd=None):
                    run_ids = list(sdk._registry.keys())
                    run_id = run_ids[-1] if run_ids else None
                    process, feed_coro = _make_process_with_complete(
                        stdout_lines, [], run_id, sdk._registry,
                    )
                    asyncio.create_task(feed_coro())
                    return process

                with patch("mcp_agent_sdk.sdk.start_cli_process", side_effect=mock_start):
                    async for event in sdk.run_agent(config):
                        if isinstance(event, AgentResult):
                            final_result = event

            assert final_result is not None
            assert isinstance(final_result, AgentResult)
            assert final_result.status == "completed"
            assert final_result.message == "task done"
            assert final_result.session_id == "sess-test"
            assert final_result.agent_run_id != ""

        finally:
            await sdk.shutdown()
