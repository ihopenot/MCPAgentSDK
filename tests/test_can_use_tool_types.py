"""Tests for can_use_tool types and default_deny_can_use_tool function."""

from __future__ import annotations

import asyncio
from typing import Any

from mcp_agent_sdk.types import (
    CanUseToolOptions,
    PermissionResultAllow,
    PermissionResultDeny,
    default_deny_can_use_tool,
)


class TestCanUseToolOptions:
    def test_construction_with_required_fields(self) -> None:
        opts = CanUseToolOptions(tool_use_id="tu_123")
        assert opts.tool_use_id == "tu_123"
        assert opts.agent_id is None

    def test_construction_with_all_fields(self) -> None:
        opts = CanUseToolOptions(tool_use_id="tu_456", agent_id="agent_1")
        assert opts.tool_use_id == "tu_456"
        assert opts.agent_id == "agent_1"


class TestPermissionResultAllow:
    def test_default_values(self) -> None:
        result = PermissionResultAllow()
        assert result.behavior == "allow"
        assert result.updated_input is None

    def test_with_updated_input(self) -> None:
        result = PermissionResultAllow(updated_input={"command": "ls"})
        assert result.behavior == "allow"
        assert result.updated_input == {"command": "ls"}


class TestPermissionResultDeny:
    def test_required_message(self) -> None:
        result = PermissionResultDeny(message="not allowed")
        assert result.behavior == "deny"
        assert result.message == "not allowed"
        assert result.interrupt is False

    def test_with_interrupt(self) -> None:
        result = PermissionResultDeny(message="stop", interrupt=True)
        assert result.behavior == "deny"
        assert result.message == "stop"
        assert result.interrupt is True


class TestDefaultDenyCanUseTool:
    def test_returns_deny_result(self) -> None:
        opts = CanUseToolOptions(tool_use_id="tu_789")
        result = asyncio.get_event_loop().run_until_complete(
            default_deny_can_use_tool("Bash", {"command": "rm -rf /"}, opts)
        )
        assert result.behavior == "deny"
        assert "Bash" in result.message
        assert result.interrupt is False

    def test_includes_tool_name_in_message(self) -> None:
        opts = CanUseToolOptions(tool_use_id="tu_000")
        result = asyncio.get_event_loop().run_until_complete(
            default_deny_can_use_tool("Write", {}, opts)
        )
        assert "Write" in result.message
