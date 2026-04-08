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
