# Hook Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Hook lifecycle support (PreToolUse, PostToolUse, UserPromptSubmit, Stop, SubagentStop, PreCompact) to MCPAgentSDK using stdin/stdout control protocol, while preserving existing MCP HTTP architecture for Complete/Block.

**Architecture:** Hybrid communication — existing MCP HTTP server handles Complete/Block (unchanged), new control protocol on stdin/stdout handles hooks. SDK sends initialize request with hooks config at startup, CLI sends hook_callback control requests during execution, SDK executes registered callbacks and writes responses back via stdin.

**Tech Stack:** Python 3.10+, asyncio, dataclasses, TypedDict, existing test framework (pytest + pytest-asyncio)

**Spec:** `docs/superpowers/specs/2026-04-03-hook-support-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `mcp_agent_sdk/types.py` | Modify | Add HookEvent, HookContext, HookJSONOutput, HookCallback, HookMatcher types; add `hooks` field to AgentRunConfig |
| `mcp_agent_sdk/hooks.py` | Create | Hook config building, callback execution, control protocol message construction |
| `mcp_agent_sdk/sdk.py` | Modify | Send initialize request at startup, intercept control_request in message loop, write control_response to stdin |
| `mcp_agent_sdk/__init__.py` | Modify | Export new Hook types |
| `example.py` | Modify | Add `hook_run()` example |
| `tests/test_hooks.py` | Create | Unit tests for hooks.py |
| `tests/test_sdk_hooks.py` | Create | Integration tests for hook handling in sdk.py |

Files NOT changed: `mcp_server.py`, `process.py`, `message_parser.py`, `errors.py`, `prompt_template.py`

---

### Task 1: Add Hook Types to `types.py`

**Files:**
- Modify: `mcp_agent_sdk/types.py`
- Test: `tests/test_types.py`

- [ ] **Step 1: Write tests for new Hook types**

Add to `tests/test_types.py`:

```python
from mcp_agent_sdk.types import (
    HookContext,
    HookMatcher,
)


class TestHookTypes:
    """Hook-related type definitions."""

    def test_hook_matcher_defaults(self):
        m = HookMatcher()
        assert m.matcher is None
        assert m.hooks == []
        assert m.timeout is None

    def test_hook_matcher_with_values(self):
        async def dummy_hook(hook_input, tool_use_id, context):
            return {"continue_": True}

        m = HookMatcher(matcher="Bash", hooks=[dummy_hook], timeout=30.0)
        assert m.matcher == "Bash"
        assert len(m.hooks) == 1
        assert m.timeout == 30.0

    def test_agent_run_config_hooks_default_none(self):
        from mcp_agent_sdk.types import AgentRunConfig
        config = AgentRunConfig(prompt="test")
        assert config.hooks is None

    def test_agent_run_config_hooks_with_value(self):
        from mcp_agent_sdk.types import AgentRunConfig

        async def dummy_hook(hook_input, tool_use_id, context):
            return {"continue_": True}

        config = AgentRunConfig(
            prompt="test",
            hooks={
                "PreToolUse": [HookMatcher(matcher="Bash", hooks=[dummy_hook])],
            },
        )
        assert "PreToolUse" in config.hooks
        assert len(config.hooks["PreToolUse"]) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /d/work/MCPAgentSDK && python -m pytest tests/test_types.py::TestHookTypes -v`
Expected: FAIL — `ImportError: cannot import name 'HookMatcher'`

- [ ] **Step 3: Add Hook types to `types.py`**

Add the following imports at the top of `mcp_agent_sdk/types.py` (after existing imports):

```python
from collections.abc import Awaitable, Callable
from typing import Any, Literal, NotRequired
from typing_extensions import TypedDict as ExtTypedDict
```

Note: The file already imports `Callable` from `collections.abc` and `Any` from `typing`. Only add the missing ones: `Awaitable`, `Literal`, `NotRequired`. For `TypedDict` with `NotRequired`, use `typing_extensions.TypedDict` if Python <3.11, or `typing.TypedDict` if >=3.11. Since the project targets Python 3.10+, use `typing_extensions`. However, check if `typing_extensions` is already a dependency — if not, use `typing.TypedDict` with `total=False` instead.

Actually, looking at the native SDK, it uses `NotRequired` from `typing`. Python 3.11+ has it. Since the project targets 3.10+, use the conditional approach. But simpler: just use `total=False` on the TypedDict like the spec says.

Add before the `AgentRunConfig` class in `mcp_agent_sdk/types.py`:

```python
# ---------------------------------------------------------------------------
# Hook types — lifecycle hooks for controlling agent behavior
# ---------------------------------------------------------------------------

HookEvent = (
    Literal["PreToolUse"]
    | Literal["PostToolUse"]
    | Literal["UserPromptSubmit"]
    | Literal["Stop"]
    | Literal["SubagentStop"]
    | Literal["PreCompact"]
)


class HookContext(TypedDict):
    """Context information for hook callbacks."""
    signal: Any | None


class HookJSONOutput(TypedDict, total=False):
    """Hook callback return value. All fields are optional."""
    continue_: bool
    suppressOutput: bool
    stopReason: str
    decision: str
    reason: str


HookCallback = Callable[
    [Any, str | None, HookContext],
    Awaitable[HookJSONOutput],
]


@dataclass
class HookMatcher:
    """Hook matcher — matches tool names or events and routes to callbacks."""
    matcher: str | None = None
    hooks: list[HookCallback] = field(default_factory=list)
    timeout: float | None = None
```

This requires adding these imports to the top of `types.py`:

```python
from collections.abc import Awaitable, Callable
from typing import Any, Literal

# Python 3.10 compatible TypedDict
try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict
```

Replace the existing `from collections.abc import Callable` and `from typing import Any` lines with the expanded versions.

Then add the `hooks` field to `AgentRunConfig`:

```python
@dataclass
class AgentRunConfig:
    """Configuration for a single run_agent() invocation."""

    prompt: str
    validate_fn: Callable[[str], tuple[bool, str]] | None = None
    on_complete: Callable[[str], None] | None = None
    on_block: Callable[[str], None] | None = None
    max_retries: int = 3
    model: str | None = None
    permission_mode: str = "bypassPermissions"
    cwd: str | None = None
    allowed_tools: list[str] | None = None
    mcp_servers: dict[str, Any] = field(default_factory=dict)
    cli_path: str = "codebuddy"
    extra_args: dict[str, str | None] = field(default_factory=dict)
    timeout: float | None = None
    hooks: dict[HookEvent, list[HookMatcher]] | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /d/work/MCPAgentSDK && python -m pytest tests/test_types.py -v`
Expected: ALL PASS (both existing and new tests)

- [ ] **Step 5: Commit**

```bash
git add mcp_agent_sdk/types.py tests/test_types.py
git commit -m "feat: add Hook type definitions (HookEvent, HookContext, HookJSONOutput, HookCallback, HookMatcher)"
```

---

### Task 2: Create `hooks.py` Module

**Files:**
- Create: `mcp_agent_sdk/hooks.py`
- Create: `tests/test_hooks.py`

- [ ] **Step 1: Write tests for `build_hooks_config`**

Create `tests/test_hooks.py`:

```python
"""Tests for hooks module: config building, callback execution, protocol messages."""

import pytest

from mcp_agent_sdk.hooks import (
    build_control_response,
    build_hooks_config,
    build_initialize_request,
    execute_hook,
)
from mcp_agent_sdk.types import HookMatcher


# --- Helpers ---

async def _allow_hook(hook_input, tool_use_id, context):
    return {"continue_": True}


async def _block_hook(hook_input, tool_use_id, context):
    return {"continue_": False, "reason": "blocked by test"}


async def _raising_hook(hook_input, tool_use_id, context):
    raise ValueError("hook exploded")


# --- build_hooks_config tests ---

class TestBuildHooksConfig:

    def test_none_hooks_returns_none_and_empty_registry(self):
        config, callbacks = build_hooks_config(None)
        assert config is None
        assert callbacks == {}

    def test_empty_dict_returns_none_and_empty_registry(self):
        config, callbacks = build_hooks_config({})
        assert config is None
        assert callbacks == {}

    def test_single_event_single_matcher_single_hook(self):
        hooks = {
            "PreToolUse": [HookMatcher(matcher="Bash", hooks=[_allow_hook])],
        }
        config, callbacks = build_hooks_config(hooks)

        assert config is not None
        assert "PreToolUse" in config
        assert len(config["PreToolUse"]) == 1
        assert config["PreToolUse"][0]["matcher"] == "Bash"
        assert config["PreToolUse"][0]["hookCallbackIds"] == ["hook_PreToolUse_0_0"]
        assert config["PreToolUse"][0]["timeout"] is None

        assert "hook_PreToolUse_0_0" in callbacks
        assert callbacks["hook_PreToolUse_0_0"] is _allow_hook

    def test_single_event_single_matcher_multiple_hooks(self):
        hooks = {
            "PreToolUse": [
                HookMatcher(matcher="Bash", hooks=[_allow_hook, _block_hook]),
            ],
        }
        config, callbacks = build_hooks_config(hooks)

        ids = config["PreToolUse"][0]["hookCallbackIds"]
        assert ids == ["hook_PreToolUse_0_0", "hook_PreToolUse_0_1"]
        assert callbacks["hook_PreToolUse_0_0"] is _allow_hook
        assert callbacks["hook_PreToolUse_0_1"] is _block_hook

    def test_multiple_matchers_per_event(self):
        hooks = {
            "PreToolUse": [
                HookMatcher(matcher="Bash", hooks=[_allow_hook]),
                HookMatcher(matcher=None, hooks=[_block_hook]),
            ],
        }
        config, callbacks = build_hooks_config(hooks)

        assert len(config["PreToolUse"]) == 2
        assert config["PreToolUse"][0]["hookCallbackIds"] == ["hook_PreToolUse_0_0"]
        assert config["PreToolUse"][1]["matcher"] is None
        assert config["PreToolUse"][1]["hookCallbackIds"] == ["hook_PreToolUse_1_0"]

    def test_multiple_events(self):
        hooks = {
            "PreToolUse": [HookMatcher(matcher="Bash", hooks=[_allow_hook])],
            "PostToolUse": [HookMatcher(matcher=None, hooks=[_block_hook])],
        }
        config, callbacks = build_hooks_config(hooks)

        assert "PreToolUse" in config
        assert "PostToolUse" in config
        assert "hook_PreToolUse_0_0" in callbacks
        assert "hook_PostToolUse_0_0" in callbacks

    def test_timeout_is_preserved(self):
        hooks = {
            "PreToolUse": [
                HookMatcher(matcher="Bash", hooks=[_allow_hook], timeout=30.0),
            ],
        }
        config, _ = build_hooks_config(hooks)
        assert config["PreToolUse"][0]["timeout"] == 30.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /d/work/MCPAgentSDK && python -m pytest tests/test_hooks.py::TestBuildHooksConfig -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mcp_agent_sdk.hooks'`

- [ ] **Step 3: Create `mcp_agent_sdk/hooks.py` with `build_hooks_config`**

Create `mcp_agent_sdk/hooks.py`:

```python
"""Hook support: config building, callback execution, control protocol messages."""

from __future__ import annotations

from typing import Any

from mcp_agent_sdk.types import HookCallback, HookMatcher


def build_hooks_config(
    hooks: dict[Any, list[HookMatcher]] | None,
) -> tuple[dict[str, list[dict[str, Any]]] | None, dict[str, HookCallback]]:
    """Build hooks configuration for CLI and callback registry.

    Flattens the nested {HookEvent: [HookMatcher]} structure into:
    - config: JSON-serializable dict to send to CLI in the initialize request
    - callbacks: {callback_id: hook_function} mapping for runtime lookup

    Returns:
        Tuple of (config_for_cli, callback_registry).
        config_for_cli is None if hooks is None or empty.
    """
    callbacks: dict[str, HookCallback] = {}

    if not hooks:
        return None, callbacks

    config: dict[str, list[dict[str, Any]]] = {}

    for event, matchers in hooks.items():
        event_str = str(event)
        matcher_configs = []

        for i, m in enumerate(matchers):
            callback_ids = []
            for j, hook in enumerate(m.hooks):
                callback_id = f"hook_{event_str}_{i}_{j}"
                callback_ids.append(callback_id)
                callbacks[callback_id] = hook

            matcher_configs.append(
                {
                    "matcher": m.matcher,
                    "hookCallbackIds": callback_ids,
                    "timeout": m.timeout,
                }
            )

        config[event_str] = matcher_configs

    return (config if config else None), callbacks


async def execute_hook(
    callback_id: str,
    hook_input: dict[str, Any],
    tool_use_id: str | None,
    hook_callbacks: dict[str, HookCallback],
) -> dict[str, Any]:
    """Execute a hook callback by looking up in the callback registry.

    Args:
        callback_id: The deterministic ID of the hook callback.
        hook_input: Input data from the CLI (tool name, args, etc.).
        tool_use_id: The tool use ID if applicable, None otherwise.
        hook_callbacks: The callback registry from build_hooks_config.

    Returns:
        Dict with hook response. Always includes "continue" key.
        On missing callback: {"continue": True} (pass-through).
        On exception: {"continue": False, "stopReason": error_message}.
    """
    hook = hook_callbacks.get(callback_id)
    if not hook:
        return {"continue": True}

    try:
        result = await hook(hook_input, tool_use_id, {"signal": None})
        output = dict(result)
        # Map Python-safe key 'continue_' back to 'continue' for CLI protocol
        if "continue_" in output:
            output["continue"] = output.pop("continue_")
        return output
    except Exception as e:
        return {"continue": False, "stopReason": str(e)}


def build_control_response(request_id: str, response: dict[str, Any]) -> dict[str, Any]:
    """Build a success control response envelope.

    Args:
        request_id: The request ID from the incoming control request.
        response: The response payload (hook result, etc.).

    Returns:
        Complete control_response JSON-serializable dict.
    """
    return {
        "type": "control_response",
        "response": {
            "subtype": "success",
            "request_id": request_id,
            "response": response,
        },
    }


def build_initialize_request(
    hooks_config: dict[str, list[dict[str, Any]]] | None,
    request_id: str,
) -> dict[str, Any]:
    """Build an initialize control request with hooks configuration.

    Args:
        hooks_config: The CLI-facing hooks config from build_hooks_config.
        request_id: Unique ID for this request.

    Returns:
        Complete control_request JSON-serializable dict.
    """
    return {
        "type": "control_request",
        "request_id": request_id,
        "request": {
            "subtype": "initialize",
            "hooks": hooks_config,
            "protocolVersion": "1.0",
        },
    }
```

- [ ] **Step 4: Run `build_hooks_config` tests**

Run: `cd /d/work/MCPAgentSDK && python -m pytest tests/test_hooks.py::TestBuildHooksConfig -v`
Expected: ALL PASS

- [ ] **Step 5: Write tests for `execute_hook`**

Append to `tests/test_hooks.py`:

```python
# --- execute_hook tests ---

class TestExecuteHook:

    @pytest.mark.asyncio
    async def test_missing_callback_returns_continue_true(self):
        result = await execute_hook("nonexistent_id", {}, None, {})
        assert result == {"continue": True}

    @pytest.mark.asyncio
    async def test_successful_hook_with_continue_true(self):
        registry = {"hook_PreToolUse_0_0": _allow_hook}
        result = await execute_hook("hook_PreToolUse_0_0", {}, None, registry)
        assert result == {"continue": True}

    @pytest.mark.asyncio
    async def test_successful_hook_with_continue_false(self):
        registry = {"hook_PreToolUse_0_0": _block_hook}
        result = await execute_hook("hook_PreToolUse_0_0", {}, None, registry)
        assert result["continue"] is False
        assert result["reason"] == "blocked by test"

    @pytest.mark.asyncio
    async def test_continue_underscore_mapped_to_continue(self):
        """continue_ in Python output becomes continue in JSON."""
        registry = {"hook_PreToolUse_0_0": _allow_hook}
        result = await execute_hook("hook_PreToolUse_0_0", {}, None, registry)
        assert "continue" in result
        assert "continue_" not in result

    @pytest.mark.asyncio
    async def test_hook_receives_correct_arguments(self):
        received = {}

        async def capture_hook(hook_input, tool_use_id, context):
            received["hook_input"] = hook_input
            received["tool_use_id"] = tool_use_id
            received["context"] = context
            return {"continue_": True}

        registry = {"cb1": capture_hook}
        await execute_hook("cb1", {"tool": "Bash"}, "tu_123", registry)

        assert received["hook_input"] == {"tool": "Bash"}
        assert received["tool_use_id"] == "tu_123"
        assert received["context"] == {"signal": None}

    @pytest.mark.asyncio
    async def test_exception_returns_continue_false_with_reason(self):
        registry = {"hook_PreToolUse_0_0": _raising_hook}
        result = await execute_hook("hook_PreToolUse_0_0", {}, None, registry)
        assert result["continue"] is False
        assert "hook exploded" in result["stopReason"]
```

- [ ] **Step 6: Run `execute_hook` tests**

Run: `cd /d/work/MCPAgentSDK && python -m pytest tests/test_hooks.py::TestExecuteHook -v`
Expected: ALL PASS

- [ ] **Step 7: Write tests for protocol message builders**

Append to `tests/test_hooks.py`:

```python
# --- Protocol message builder tests ---

class TestBuildControlResponse:

    def test_structure(self):
        resp = build_control_response("req_123", {"continue": True})
        assert resp["type"] == "control_response"
        assert resp["response"]["subtype"] == "success"
        assert resp["response"]["request_id"] == "req_123"
        assert resp["response"]["response"] == {"continue": True}

    def test_with_complex_response(self):
        payload = {"continue": False, "stopReason": "blocked"}
        resp = build_control_response("req_456", payload)
        assert resp["response"]["response"] == payload


class TestBuildInitializeRequest:

    def test_structure_with_hooks(self):
        hooks_config = {
            "PreToolUse": [
                {"matcher": "Bash", "hookCallbackIds": ["hook_PreToolUse_0_0"], "timeout": None},
            ],
        }
        req = build_initialize_request(hooks_config, "init_001")

        assert req["type"] == "control_request"
        assert req["request_id"] == "init_001"
        assert req["request"]["subtype"] == "initialize"
        assert req["request"]["hooks"] == hooks_config
        assert req["request"]["protocolVersion"] == "1.0"

    def test_structure_with_none_hooks(self):
        req = build_initialize_request(None, "init_002")
        assert req["request"]["hooks"] is None
```

- [ ] **Step 8: Run all hooks tests**

Run: `cd /d/work/MCPAgentSDK && python -m pytest tests/test_hooks.py -v`
Expected: ALL PASS

- [ ] **Step 9: Commit**

```bash
git add mcp_agent_sdk/hooks.py tests/test_hooks.py
git commit -m "feat: add hooks module with build_hooks_config, execute_hook, and protocol builders"
```

---

### Task 3: Integrate Hooks into `sdk.py`

**Files:**
- Modify: `mcp_agent_sdk/sdk.py`
- Create: `tests/test_sdk_hooks.py`

- [ ] **Step 1: Write integration tests for hook handling in `run_agent()`**

Create `tests/test_sdk_hooks.py`:

```python
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
    """run_agent with no hooks should work exactly as before — no initialize sent."""
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

            # Check stdin writes — should only have the prompt, no initialize request
            if captured_proc:
                writes = captured_proc._stdin_writes
                # Decode all writes and check none is a control_request
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

            # Check stdin writes — should contain an initialize control_request
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
                                # Verify hooks config is present
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
        # The hook_request will be interleaved via _make_fake_process
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /d/work/MCPAgentSDK && python -m pytest tests/test_sdk_hooks.py -v`
Expected: FAIL — hooks not integrated yet, initialize not sent, control_request not handled

- [ ] **Step 3: Modify `sdk.py` to support hooks**

Changes to `mcp_agent_sdk/sdk.py`:

**Add imports** (at top, after existing imports):

```python
import json

from mcp_agent_sdk.hooks import (
    build_control_response,
    build_hooks_config,
    build_initialize_request,
    execute_hook,
)
```

**Add helper method** (inside `MCPAgentSDK` class, before `run_agent`):

```python
    @staticmethod
    async def _write_to_stdin(process: asyncio.subprocess.Process, data: dict) -> None:
        """Write a JSON message to the subprocess stdin."""
        if process.stdin and not process.stdin.is_closing():
            process.stdin.write((json.dumps(data) + "\n").encode())
            await process.stdin.drain()
```

**Modify `run_agent()`** — after the subprocess is started and prompt is sent (after line 135 in current code), add hook initialization:

```python
        # Initialize hooks via control protocol if configured
        hook_callbacks: dict[str, Any] = {}
        if config.hooks:
            hooks_config, hook_callbacks = build_hooks_config(config.hooks)
            if hooks_config is not None:
                init_request = build_initialize_request(
                    hooks_config, f"init_{agent_run_id}"
                )
                await self._write_to_stdin(process, init_request)
```

**Modify the message loop** — replace the section from `line = raw_line.decode(...)` through `event = parse_line(line)` with logic that first checks for control_request:

Replace this block in the while loop (after `line = raw_line.decode(...)` and the stdout_tail logic):

```python
                # Check for control_request before parsing as stream event
                try:
                    raw_data = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    raw_data = None

                if isinstance(raw_data, dict) and raw_data.get("type") == "control_request":
                    # Handle hook callback control request
                    request_id = raw_data.get("request_id", "")
                    request = raw_data.get("request", {})
                    subtype = request.get("subtype", "")

                    if subtype == "hook_callback":
                        callback_id = request.get("callback_id", "")
                        hook_input = request.get("input", {})
                        tool_use_id = request.get("tool_use_id")

                        response = await execute_hook(
                            callback_id, hook_input, tool_use_id, hook_callbacks
                        )
                        control_resp = build_control_response(request_id, response)
                        await self._write_to_stdin(process, control_resp)

                    # Don't yield control messages as stream events
                    continue

                event = parse_line(line)
```

The key structure change in the while loop is:

```
# BEFORE (original):
event = parse_line(line)
if event is None:
    continue

# AFTER (with hooks):
try:
    raw_data = json.loads(line)
except (json.JSONDecodeError, ValueError):
    raw_data = None

if isinstance(raw_data, dict) and raw_data.get("type") == "control_request":
    # ... handle hook callback ...
    continue

event = parse_line(line)
if event is None:
    continue
```

Everything after `if event is None: continue` remains exactly the same.

- [ ] **Step 4: Run integration tests**

Run: `cd /d/work/MCPAgentSDK && python -m pytest tests/test_sdk_hooks.py -v`
Expected: ALL PASS

- [ ] **Step 5: Run ALL existing tests to verify no regressions**

Run: `cd /d/work/MCPAgentSDK && python -m pytest tests/ -v`
Expected: ALL PASS — existing tests should not be affected

- [ ] **Step 6: Commit**

```bash
git add mcp_agent_sdk/sdk.py tests/test_sdk_hooks.py
git commit -m "feat: integrate hook support into run_agent() with control protocol"
```

---

### Task 4: Export Hook Types from `__init__.py`

**Files:**
- Modify: `mcp_agent_sdk/__init__.py`

- [ ] **Step 1: Update `__init__.py` to export Hook types**

Add the Hook type imports and exports to `mcp_agent_sdk/__init__.py`:

Add to imports section:

```python
from mcp_agent_sdk.types import (
    # ... existing imports ...
    HookCallback,
    HookContext,
    HookEvent,
    HookJSONOutput,
    HookMatcher,
)
```

Add to `__all__` list:

```python
    # Hook types
    "HookCallback",
    "HookContext",
    "HookEvent",
    "HookJSONOutput",
    "HookMatcher",
```

- [ ] **Step 2: Verify imports work**

Run: `cd /d/work/MCPAgentSDK && python -c "from mcp_agent_sdk import HookMatcher, HookCallback, HookContext, HookJSONOutput, HookEvent; print('All hook types importable')"`
Expected: `All hook types importable`

- [ ] **Step 3: Run all tests**

Run: `cd /d/work/MCPAgentSDK && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add mcp_agent_sdk/__init__.py
git commit -m "feat: export Hook types from mcp_agent_sdk package"
```

---

### Task 5: Add Hook Example to `example.py`

**Files:**
- Modify: `example.py`

- [ ] **Step 1: Add `hook_run()` function to `example.py`**

Add after the `claude_run()` function and before the `if __name__ == "__main__"` block:

```python
# ---------------------------------------------------------------------------
# Example 8: Hooks — control agent behavior with lifecycle hooks
# ---------------------------------------------------------------------------
async def hook_run() -> None:
    """Use a PreToolUse hook to block dangerous shell commands.

    The hook intercepts Bash tool calls and blocks commands containing
    'rm -rf', 'mkfs', or 'dd if='. Safe commands pass through normally.
    """
    from mcp_agent_sdk import HookMatcher

    sdk = MCPAgentSDK()
    await sdk.init()

    async def block_dangerous_commands(hook_input, tool_use_id, context):
        """Block dangerous Bash commands before they execute."""
        input_data = hook_input.get("input", {})
        command = input_data.get("command", "")
        dangerous = ["rm -rf", "mkfs", "dd if="]
        if any(d in command for d in dangerous):
            print(f"  🛡️  Hook blocked: {command}")
            return {
                "continue_": False,
                "decision": "block",
                "reason": f"Blocked dangerous command: {command}",
            }
        return {"continue_": True}

    config = AgentRunConfig(
        prompt="List files in the current directory and show disk usage",
        hooks={
            "PreToolUse": [
                HookMatcher(
                    matcher="Bash",
                    hooks=[block_dangerous_commands],
                )
            ],
        },
        permission_mode="bypassPermissions",
    )

    try:
        async for event in sdk.run_agent(config):
            if isinstance(event, AgentResult):
                print(f"\n✅ Done — status: {event.status}, message: {event.message}")
            else:
                print_event(event)
    except AgentStartupError as e:
        print(f"❌ Startup failed: {e}")
    except AgentProcessError as e:
        print(f"❌ Process crashed: {e}")

    await sdk.shutdown()
```

- [ ] **Step 2: Register in examples dictionary**

In the `if __name__ == "__main__"` block, add `"hooks"` to the `examples` dict:

```python
    examples = {
        "basic": basic_run,
        "validated": validated_run,
        "callback": callback_run,
        "concurrent": concurrent_runs,
        "advanced": advanced_run,
        "custom_mcp": custom_mcp_run,
        "claude": claude_run,
        "hooks": hook_run,
    }
```

- [ ] **Step 3: Verify syntax**

Run: `cd /d/work/MCPAgentSDK && python -c "import example; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Run all tests one final time**

Run: `cd /d/work/MCPAgentSDK && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add example.py
git commit -m "feat: add hook_run() example demonstrating PreToolUse hook for blocking dangerous commands"
```

---

### Task 6: Final Verification

**Files:** None (verification only)

- [ ] **Step 1: Run full test suite**

Run: `cd /d/work/MCPAgentSDK && python -m pytest tests/ -v --tb=short`
Expected: ALL PASS, no warnings related to hook changes

- [ ] **Step 2: Verify all Hook types are importable from the public API**

Run: `cd /d/work/MCPAgentSDK && python -c "from mcp_agent_sdk import MCPAgentSDK, AgentRunConfig, HookMatcher, HookCallback, HookContext, HookJSONOutput, HookEvent, AgentResult; print('All exports OK')"`
Expected: `All exports OK`

- [ ] **Step 3: Verify example syntax**

Run: `cd /d/work/MCPAgentSDK && python example.py --help 2>&1 || python -c "import example; print(list(example.examples.keys()) if hasattr(example, 'examples') else 'no examples dict')"`
Expected: Should list all examples including `hooks`

- [ ] **Step 4: Review change summary**

Verify the following files were changed:
- `mcp_agent_sdk/types.py` — Hook types added
- `mcp_agent_sdk/hooks.py` — New module created
- `mcp_agent_sdk/sdk.py` — Hook initialization and control_request handling
- `mcp_agent_sdk/__init__.py` — Hook type exports
- `example.py` — hook_run() example added
- `tests/test_types.py` — Hook type tests
- `tests/test_hooks.py` — hooks module tests
- `tests/test_sdk_hooks.py` — SDK integration tests

Verify these files were NOT changed:
- `mcp_agent_sdk/mcp_server.py`
- `mcp_agent_sdk/process.py`
- `mcp_agent_sdk/message_parser.py`
- `mcp_agent_sdk/errors.py`
- `mcp_agent_sdk/prompt_template.py`
