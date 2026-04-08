"""Integration tests for hook support in MCPAgentSDK.run_agent()."""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from mcp_agent_sdk.sdk import MCPAgentSDK
from mcp_agent_sdk.types import AgentResult, AgentRunConfig, HookMatcher


async def _allow_all_hook(hook_input, tool_use_id, context):
    return {"continue_": True}


async def _block_bash_hook(hook_input, tool_use_id, context):
    input_data = hook_input.get("input", {})
    command = input_data.get("command", "")
    if "rm -rf" in command:
        return {"continue_": False, "reason": "dangerous command blocked"}
    return {"continue_": True}


def _make_fake_process(stdout_lines: list[str], hook_requests: list[dict] | None = None):
    """Create a mock subprocess that emits given stdout lines.

    If hook_requests is provided, they are interleaved: after the first
    stream-json line, each hook_request is emitted (one per readline call),
    then remaining stream-json lines follow.
    """
    all_lines = []
    for line in stdout_lines:
        all_lines.append((json.dumps(line) + "\n").encode() if isinstance(line, dict) else (line + "\n").encode())

    if hook_requests:
        # Insert hook requests after the first stream-json line
        hook_lines = [(json.dumps(hr) + "\n").encode() for hr in hook_requests]
        all_lines = all_lines[:1] + hook_lines + all_lines[1:]

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

        # Track stdin writes
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


@pytest.mark.asyncio
async def test_run_agent_without_hooks_backward_compatible():
    """run_agent with no hooks should work exactly as before - no initialize sent."""
    sdk = MCPAgentSDK()
    await sdk.init(port=0)

    stdout_lines = [
        {"type": "system", "subtype": "init", "session_id": "s1"},
    ]

    fake_start = _make_fake_process(stdout_lines)
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
            config = AgentRunConfig(prompt="test", hooks=None)
            messages = []
            try:
                async for msg in sdk.run_agent(config):
                    messages.append(msg)
            except Exception:
                pass  # Process ends without Complete/Block, that's OK for this test

            # Check stdin writes - should only have the prompt, no initialize request
            if captured_proc:
                writes = captured_proc._stdin_writes
                for w in writes:
                    decoded = w.decode("utf-8", errors="replace")
                    for line in decoded.strip().split("\n"):
                        if line.strip():
                            try:
                                data = json.loads(line)
                                assert data.get("type") != "control_request", \
                                    "No control_request should be sent when hooks=None"
                            except json.JSONDecodeError:
                                pass
    finally:
        await sdk.shutdown()


@pytest.mark.asyncio
async def test_run_agent_with_hooks_sends_initialize():
    """run_agent with hooks should send an initialize control_request via stdin."""
    sdk = MCPAgentSDK()
    await sdk.init(port=0)

    stdout_lines = [
        {"type": "system", "subtype": "init", "session_id": "s1"},
    ]

    fake_start = _make_fake_process(stdout_lines)
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
            config = AgentRunConfig(
                prompt="test",
                hooks={
                    "PreToolUse": [HookMatcher(matcher="Bash", hooks=[_allow_all_hook])],
                },
            )
            messages = []
            try:
                async for msg in sdk.run_agent(config):
                    messages.append(msg)
            except Exception:
                pass

            # Check stdin writes - should contain an initialize control_request
            assert captured_proc is not None
            writes = captured_proc._stdin_writes
            found_init = False
            for w in writes:
                decoded = w.decode("utf-8", errors="replace")
                for line in decoded.strip().split("\n"):
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if (data.get("type") == "control_request"
                                    and data.get("request", {}).get("subtype") == "initialize"):
                                found_init = True
                                hooks_cfg = data["request"]["hooks"]
                                assert "PreToolUse" in hooks_cfg
                                assert hooks_cfg["PreToolUse"][0]["matcher"] == "Bash"
                        except json.JSONDecodeError:
                            pass
            assert found_init, "Expected an initialize control_request in stdin writes"
    finally:
        await sdk.shutdown()


@pytest.mark.asyncio
async def test_hook_callback_is_executed_and_response_sent():
    """When CLI sends a hook_callback control_request, SDK should execute the
    hook and write a control_response back to stdin."""
    sdk = MCPAgentSDK()
    await sdk.init(port=0)

    hook_request = {
        "type": "control_request",
        "request_id": "hook_req_1",
        "request": {
            "subtype": "hook_callback",
            "callback_id": "hook_PreToolUse_0_0",
            "input": {"tool_name": "Bash", "input": {"command": "ls"}},
            "tool_use_id": "tu_001",
        },
    }

    stdout_lines = [
        {"type": "system", "subtype": "init", "session_id": "s1"},
    ]

    fake_start = _make_fake_process(stdout_lines, hook_requests=[hook_request])
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
            config = AgentRunConfig(
                prompt="test",
                hooks={
                    "PreToolUse": [HookMatcher(matcher="Bash", hooks=[_allow_all_hook])],
                },
            )
            messages = []
            try:
                async for msg in sdk.run_agent(config):
                    messages.append(msg)
            except Exception:
                pass

            # Find the control_response in stdin writes
            assert captured_proc is not None
            writes = captured_proc._stdin_writes
            found_response = False
            for w in writes:
                decoded = w.decode("utf-8", errors="replace")
                for line in decoded.strip().split("\n"):
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if data.get("type") == "control_response":
                                found_response = True
                                resp = data["response"]
                                assert resp["request_id"] == "hook_req_1"
                                assert resp["response"]["continue"] is True
                        except json.JSONDecodeError:
                            pass
            assert found_response, "Expected a control_response in stdin writes"
    finally:
        await sdk.shutdown()


@pytest.mark.asyncio
async def test_control_requests_are_not_yielded_as_events():
    """Control requests should be handled internally, not yielded to the caller."""
    sdk = MCPAgentSDK()
    await sdk.init(port=0)

    hook_request = {
        "type": "control_request",
        "request_id": "hook_req_2",
        "request": {
            "subtype": "hook_callback",
            "callback_id": "hook_PreToolUse_0_0",
            "input": {},
            "tool_use_id": None,
        },
    }

    stdout_lines = [
        {"type": "system", "subtype": "init", "session_id": "s1"},
    ]

    fake_start = _make_fake_process(stdout_lines, hook_requests=[hook_request])

    try:
        with (
            patch("mcp_agent_sdk.sdk.find_codebuddy_cli", return_value="codebuddy"),
            patch("mcp_agent_sdk.sdk.start_cli_process", side_effect=fake_start),
        ):
            config = AgentRunConfig(
                prompt="test",
                hooks={
                    "PreToolUse": [HookMatcher(matcher="Bash", hooks=[_allow_all_hook])],
                },
            )
            messages = []
            try:
                async for msg in sdk.run_agent(config):
                    messages.append(msg)
            except Exception:
                pass

            # No message should have type "control_request"
            for msg in messages:
                assert not hasattr(msg, "type") or getattr(msg, "type", None) != "control_request"
    finally:
        await sdk.shutdown()
