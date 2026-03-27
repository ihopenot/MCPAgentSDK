"""Tests for sdk.py error handling: startup crash and unexpected exit raise exceptions."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_agent_sdk.errors import AgentProcessError, AgentStartupError
from mcp_agent_sdk.types import AgentRunConfig


def _make_process(stdout_lines: list[str], stderr_lines: list[str], returncode: int):
    """Create a mock subprocess with given stdout/stderr/returncode."""
    stdout_data = "".join(line + "\n" for line in stdout_lines).encode()
    stderr_data = "".join(line + "\n" for line in stderr_lines).encode()

    process = MagicMock()
    process.returncode = None  # initially running

    # stdout stream
    stdout_reader = asyncio.StreamReader()
    stdout_reader.feed_data(stdout_data)
    stdout_reader.feed_eof()
    process.stdout = stdout_reader

    # stderr stream
    stderr_reader = asyncio.StreamReader()
    stderr_reader.feed_data(stderr_data)
    stderr_reader.feed_eof()
    process.stderr = stderr_reader

    # stdin
    process.stdin = MagicMock()
    process.stdin.write = MagicMock()
    process.stdin.drain = AsyncMock()
    process.stdin.close = MagicMock()

    async def _wait():
        process.returncode = returncode
        return returncode

    process.wait = _wait
    process.terminate = MagicMock()
    process.kill = MagicMock()

    return process


class TestAgentStartupCrash:
    """When process exits immediately with no stdout, raise AgentStartupError."""

    @pytest.mark.asyncio
    async def test_startup_crash_raises(self):
        from mcp_agent_sdk.sdk import MCPAgentSDK

        sdk = MCPAgentSDK()
        await sdk.init()

        try:
            # Process that exits immediately with error
            process = _make_process(
                stdout_lines=[],
                stderr_lines=["Error: invalid config", "Abort"],
                returncode=1,
            )

            config = AgentRunConfig(prompt="do something")

            with patch("mcp_agent_sdk.sdk.find_codebuddy_cli", return_value="/fake/cli"):
                with patch("mcp_agent_sdk.sdk.start_cli_process", return_value=process):
                    with pytest.raises(AgentStartupError) as exc_info:
                        async for _ in sdk.run_agent(config):
                            pass

            assert "Error: invalid config" in exc_info.value.stderr
            assert exc_info.value.exit_code == 1
        finally:
            await sdk.shutdown()


class TestAgentProcessExitWithoutComplete:
    """When process exits mid-run without Complete/Block, raise AgentProcessError."""

    @pytest.mark.asyncio
    async def test_unexpected_exit_raises(self):
        from mcp_agent_sdk.sdk import MCPAgentSDK

        sdk = MCPAgentSDK()
        await sdk.init()

        try:
            # Process that produces some output then exits
            stdout_lines = [
                json.dumps({"type": "system", "subtype": "init", "session_id": "sess-1"}),
                json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Working..."}]}}),
            ]
            process = _make_process(
                stdout_lines=stdout_lines,
                stderr_lines=["Warning: something went wrong"],
                returncode=137,
            )

            config = AgentRunConfig(prompt="do something")

            with patch("mcp_agent_sdk.sdk.find_codebuddy_cli", return_value="/fake/cli"):
                with patch("mcp_agent_sdk.sdk.start_cli_process", return_value=process):
                    with pytest.raises(AgentProcessError) as exc_info:
                        async for _ in sdk.run_agent(config):
                            pass

            assert exc_info.value.exit_code == 137
            assert "something went wrong" in exc_info.value.stderr
        finally:
            await sdk.shutdown()
