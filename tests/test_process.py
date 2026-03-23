"""Tests for subprocess management: argument construction and process creation."""

import json

import pytest

from mcp_agent_sdk.process import build_cli_args
from mcp_agent_sdk.types import AgentRunConfig


def test_build_cli_args_minimal():
    """Minimal config should produce base args with prompt."""
    config = AgentRunConfig(prompt="do something")
    args = build_cli_args(
        config=config,
        full_prompt="injected prompt",
        mcp_server_url="http://127.0.0.1:9000/mcp",
    )
    assert "--input-format=stream-json" in args
    assert "--output-format=stream-json" in args
    assert "--print" in args
    assert "--permission-mode" in args
    assert "bypassPermissions" in args

    # Check mcp-config is a JSON string containing the server URL
    mcp_idx = args.index("--mcp-config")
    mcp_json = json.loads(args[mcp_idx + 1])
    assert "mcpServers" in mcp_json
    assert mcp_json["mcpServers"]["agent-controller"]["url"] == "http://127.0.0.1:9000/mcp"


def test_build_cli_args_with_model():
    """Model should be passed via --model flag."""
    config = AgentRunConfig(prompt="test", model="claude-sonnet-4-20250514")
    args = build_cli_args(config=config, full_prompt="p", mcp_server_url="http://localhost/mcp")
    assert "--model" in args
    model_idx = args.index("--model")
    assert args[model_idx + 1] == "claude-sonnet-4-20250514"


def test_build_cli_args_with_allowed_tools():
    """allowed_tools should be passed via --allowedTools."""
    config = AgentRunConfig(prompt="test", allowed_tools=["Read", "Write", "Bash"])
    args = build_cli_args(config=config, full_prompt="p", mcp_server_url="http://localhost/mcp")
    assert "--allowedTools" in args
    tools_idx = args.index("--allowedTools")
    assert args[tools_idx + 1] == "Read"
    assert args[tools_idx + 2] == "Write"
    assert args[tools_idx + 3] == "Bash"


def test_build_cli_args_with_extra_args():
    """extra_args should be passed as --flag value pairs."""
    config = AgentRunConfig(prompt="test", extra_args={"max-turns": "10", "verbose": None})
    args = build_cli_args(config=config, full_prompt="p", mcp_server_url="http://localhost/mcp")
    assert "--max-turns" in args
    assert "10" in args
    assert "--verbose" in args


def test_build_cli_args_prompt_via_stdin():
    """The full_prompt should NOT appear in args (sent via stdin)."""
    config = AgentRunConfig(prompt="original prompt")
    args = build_cli_args(
        config=config,
        full_prompt="injected system prompt + original prompt",
        mcp_server_url="http://localhost/mcp",
    )
    # Prompt is sent via stdin, not in args
    assert "injected system prompt + original prompt" not in args
    assert "original prompt" not in args


def test_build_cli_args_mcp_config_is_valid_json():
    """The --mcp-config value should be parseable JSON."""
    config = AgentRunConfig(prompt="test")
    args = build_cli_args(config=config, full_prompt="p", mcp_server_url="http://127.0.0.1:8080/mcp")
    mcp_idx = args.index("--mcp-config")
    mcp_val = args[mcp_idx + 1]
    parsed = json.loads(mcp_val)
    assert parsed["mcpServers"]["agent-controller"]["type"] == "streamable-http"


def test_build_cli_args_setting_sources_none():
    """Default should include --setting-sources none for isolation."""
    config = AgentRunConfig(prompt="test")
    args = build_cli_args(config=config, full_prompt="p", mcp_server_url="http://localhost/mcp")
    assert "--setting-sources" in args
    idx = args.index("--setting-sources")
    assert args[idx + 1] == "none"
