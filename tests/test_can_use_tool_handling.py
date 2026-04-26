"""Integration tests for can_use_tool handling in MCPAgentSDK.run_agent()."""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from mcp_agent_sdk.sdk import MCPAgentSDK
from mcp_agent_sdk.types import (
    AgentRunConfig,
    CanUseToolOptions,
    PermissionResultAllow,
    PermissionResultDeny,
)


def _make_can_use_tool_request(
    tool_name: str = "Bash",
    input_data: dict | None = None,
    tool_use_id: str = "tu_100",
    agent_id: str | None = None,
    request_id: str = "cut_req_1",
) -> dict:
    """Build a can_use_tool control_request as the CLI would send it."""
    return {
        "type": "control_request",
        "request_id": request_id,
        "request": {
            "subtype": "can_use_tool",
            "tool_name": tool_name,
            "input": input_data or {},
            "tool_use_id": tool_use_id,
            "agent_id": agent_id,
        },
    }


def _make_fake_process(stdout_lines: list, control_requests: list[dict] | None = None):
    """Create a mock subprocess that emits given stdout lines.

    control_requests are interleaved after the first stream-json line.
    """
    all_lines = []
    for line in stdout_lines:
        all_lines.append(
            (json.dumps(line) + "\n").encode()
            if isinstance(line, dict)
            else (line + "\n").encode()
        )

    if control_requests:
        cr_lines = [(json.dumps(cr) + "\n").encode() for cr in control_requests]
        all_lines = all_lines[:1] + cr_lines + all_lines[1:]

    line_iter = iter(all_lines)

    async def _fake_start_cli_process(cli_path, args, full_prompt, cwd=None):
        proc = AsyncMock()
        proc.returncode = None

        class FakeStdout:
            async def readline(self_stdout):
                try:
                    return next(line_iter)
                except StopIteration:
                    return b""

        proc.stdout = FakeStdout()

        stderr_reader = asyncio.StreamReader()
        stderr_reader.feed_eof()
        proc.stderr = stderr_reader

        stdin_writes = []

        class FakeStdin:
            def write(self, data):
                stdin_writes.append(data)

            async def drain(self):
                pass

            def is_closing(self):
                return False

            def close(self):
                pass

        proc.stdin = FakeStdin()
        proc._stdin_writes = stdin_writes

        def _terminate():
            proc.returncode = -1

        proc.terminate = _terminate
        proc.kill = lambda: None
        proc.wait = AsyncMock(return_value=0)
        return proc

    return _fake_start_cli_process


def _extract_control_responses(proc) -> list[dict]:
    """Extract all control_response dicts from fake process stdin writes."""
    responses = []
    for w in proc._stdin_writes:
        decoded = w.decode("utf-8", errors="replace")
        for line in decoded.strip().split("\n"):
            if line.strip():
                try:
                    data = json.loads(line)
                    if data.get("type") == "control_response":
                        responses.append(data)
                except json.JSONDecodeError:
                    pass
    return responses


@pytest.mark.asyncio
async def test_default_deny_when_no_callback():
    """When can_use_tool is None, SDK should respond with allowed=False."""
    sdk = MCPAgentSDK()
    await sdk.init(port=0)

    cr = _make_can_use_tool_request(tool_name="Bash", tool_use_id="tu_1")
    stdout_lines = [{"type": "system", "subtype": "init", "session_id": "s1"}]

    fake_start = _make_fake_process(stdout_lines, control_requests=[cr])
    captured_proc = None
    original_fake = fake_start

    async def capturing_fake(*args, **kwargs):
        nonlocal captured_proc
        captured_proc = await original_fake(*args, **kwargs)
        return captured_proc

    try:
        with (
            patch("mcp_agent_sdk.sdk.find_codebuddy_cli", return_value="codebuddy"),
            patch("mcp_agent_sdk.sdk.start_cli_process", side_effect=capturing_fake),
        ):
            config = AgentRunConfig(prompt="test", can_use_tool=None)
            try:
                async for _ in sdk.run_agent(config):
                    pass
            except Exception:
                pass

            assert captured_proc is not None
            responses = _extract_control_responses(captured_proc)
            assert len(responses) >= 1

            resp = responses[0]["response"]["response"]
            assert resp["allowed"] is False
            assert "Bash" in resp["reason"]
            assert resp["tool_use_id"] == "tu_1"
    finally:
        await sdk.shutdown()


@pytest.mark.asyncio
async def test_custom_callback_allow():
    """Custom can_use_tool returning Allow should respond with allowed=True."""
    sdk = MCPAgentSDK()
    await sdk.init(port=0)

    async def allow_all(tool_name, input_data, options):
        return PermissionResultAllow()

    cr = _make_can_use_tool_request(tool_name="Read", tool_use_id="tu_2")
    stdout_lines = [{"type": "system", "subtype": "init", "session_id": "s1"}]

    fake_start = _make_fake_process(stdout_lines, control_requests=[cr])
    captured_proc = None
    original_fake = fake_start

    async def capturing_fake(*args, **kwargs):
        nonlocal captured_proc
        captured_proc = await original_fake(*args, **kwargs)
        return captured_proc

    try:
        with (
            patch("mcp_agent_sdk.sdk.find_codebuddy_cli", return_value="codebuddy"),
            patch("mcp_agent_sdk.sdk.start_cli_process", side_effect=capturing_fake),
        ):
            config = AgentRunConfig(prompt="test", can_use_tool=allow_all)
            try:
                async for _ in sdk.run_agent(config):
                    pass
            except Exception:
                pass

            assert captured_proc is not None
            responses = _extract_control_responses(captured_proc)
            assert len(responses) >= 1

            resp = responses[0]["response"]["response"]
            assert resp["allowed"] is True
            assert resp["tool_use_id"] == "tu_2"
    finally:
        await sdk.shutdown()


@pytest.mark.asyncio
async def test_custom_callback_allow_with_updated_input():
    """Allow result with updated_input should forward updatedInput."""
    sdk = MCPAgentSDK()
    await sdk.init(port=0)

    async def modify_input(tool_name, input_data, options):
        return PermissionResultAllow(updated_input={"command": "safe_cmd"})

    cr = _make_can_use_tool_request(
        tool_name="Bash", input_data={"command": "dangerous"}, tool_use_id="tu_3"
    )
    stdout_lines = [{"type": "system", "subtype": "init", "session_id": "s1"}]

    fake_start = _make_fake_process(stdout_lines, control_requests=[cr])
    captured_proc = None
    original_fake = fake_start

    async def capturing_fake(*args, **kwargs):
        nonlocal captured_proc
        captured_proc = await original_fake(*args, **kwargs)
        return captured_proc

    try:
        with (
            patch("mcp_agent_sdk.sdk.find_codebuddy_cli", return_value="codebuddy"),
            patch("mcp_agent_sdk.sdk.start_cli_process", side_effect=capturing_fake),
        ):
            config = AgentRunConfig(prompt="test", can_use_tool=modify_input)
            try:
                async for _ in sdk.run_agent(config):
                    pass
            except Exception:
                pass

            assert captured_proc is not None
            responses = _extract_control_responses(captured_proc)
            resp = responses[0]["response"]["response"]
            assert resp["allowed"] is True
            assert resp["updatedInput"] == {"command": "safe_cmd"}
    finally:
        await sdk.shutdown()


@pytest.mark.asyncio
async def test_custom_callback_deny():
    """Custom can_use_tool returning Deny should respond with allowed=False."""
    sdk = MCPAgentSDK()
    await sdk.init(port=0)

    async def deny_bash(tool_name, input_data, options):
        return PermissionResultDeny(message="Bash not allowed", interrupt=True)

    cr = _make_can_use_tool_request(tool_name="Bash", tool_use_id="tu_4")
    stdout_lines = [{"type": "system", "subtype": "init", "session_id": "s1"}]

    fake_start = _make_fake_process(stdout_lines, control_requests=[cr])
    captured_proc = None
    original_fake = fake_start

    async def capturing_fake(*args, **kwargs):
        nonlocal captured_proc
        captured_proc = await original_fake(*args, **kwargs)
        return captured_proc

    try:
        with (
            patch("mcp_agent_sdk.sdk.find_codebuddy_cli", return_value="codebuddy"),
            patch("mcp_agent_sdk.sdk.start_cli_process", side_effect=capturing_fake),
        ):
            config = AgentRunConfig(prompt="test", can_use_tool=deny_bash)
            try:
                async for _ in sdk.run_agent(config):
                    pass
            except Exception:
                pass

            assert captured_proc is not None
            responses = _extract_control_responses(captured_proc)
            resp = responses[0]["response"]["response"]
            assert resp["allowed"] is False
            assert resp["reason"] == "Bash not allowed"
            assert resp["interrupt"] is True
            assert resp["tool_use_id"] == "tu_4"
    finally:
        await sdk.shutdown()


@pytest.mark.asyncio
async def test_callback_exception_returns_deny():
    """If can_use_tool callback raises, SDK should respond with allowed=False."""
    sdk = MCPAgentSDK()
    await sdk.init(port=0)

    async def failing_callback(tool_name, input_data, options):
        raise ValueError("callback exploded")

    cr = _make_can_use_tool_request(tool_name="Write", tool_use_id="tu_5")
    stdout_lines = [{"type": "system", "subtype": "init", "session_id": "s1"}]

    fake_start = _make_fake_process(stdout_lines, control_requests=[cr])
    captured_proc = None
    original_fake = fake_start

    async def capturing_fake(*args, **kwargs):
        nonlocal captured_proc
        captured_proc = await original_fake(*args, **kwargs)
        return captured_proc

    try:
        with (
            patch("mcp_agent_sdk.sdk.find_codebuddy_cli", return_value="codebuddy"),
            patch("mcp_agent_sdk.sdk.start_cli_process", side_effect=capturing_fake),
        ):
            config = AgentRunConfig(prompt="test", can_use_tool=failing_callback)
            try:
                async for _ in sdk.run_agent(config):
                    pass
            except Exception:
                pass

            assert captured_proc is not None
            responses = _extract_control_responses(captured_proc)
            resp = responses[0]["response"]["response"]
            assert resp["allowed"] is False
            assert "callback exploded" in resp["reason"]
            assert resp["tool_use_id"] == "tu_5"
    finally:
        await sdk.shutdown()
