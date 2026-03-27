"""Tests for message parser: parse stdout JSON lines into structured types."""

import pytest

from mcp_agent_sdk.message_parser import parse_message, parse_line
from mcp_agent_sdk.types import (
    AssistantMessage,
    ContentBlock,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
)


def test_parse_assistant_message():
    """Parse an assistant message with text content."""
    data = {
        "type": "assistant",
        "message": {
            "content": [{"type": "text", "text": "Hello world"}]
        },
        "model": "claude-sonnet-4-20250514",
    }
    msg = parse_message(data)
    assert isinstance(msg, AssistantMessage)
    assert len(msg.content) == 1
    assert isinstance(msg.content[0], TextBlock)
    assert msg.content[0].text == "Hello world"


def test_parse_tool_use_message():
    """Parse an assistant message containing a tool use block."""
    data = {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "tool_use", "id": "tu_123", "name": "Write", "input": {"path": "test.py"}}
            ]
        },
    }
    msg = parse_message(data)
    assert isinstance(msg, AssistantMessage)
    block = msg.content[0]
    assert isinstance(block, ToolUseBlock)
    assert block.name == "Write"


def test_parse_result_message():
    """Parse a result message."""
    data = {
        "type": "result",
        "session_id": "sess-abc",
        "is_error": False,
        "num_turns": 5,
        "duration_ms": 12000,
    }
    msg = parse_message(data)
    assert isinstance(msg, ResultMessage)
    assert msg.session_id == "sess-abc"
    assert msg.is_error is False


def test_parse_system_message():
    """Parse a system message."""
    data = {
        "type": "system",
        "subtype": "init",
        "data": {"session_id": "sess-xyz"},
    }
    msg = parse_message(data)
    assert isinstance(msg, SystemMessage)
    assert msg.subtype == "init"


def test_parse_error_message():
    """Parse an error message — becomes SystemMessage."""
    data = {
        "type": "error",
        "error": "something went wrong",
    }
    msg = parse_message(data)
    assert isinstance(msg, SystemMessage)
    assert msg.subtype == "error"
    assert msg.data["error"] == "something went wrong"


def test_parse_unknown_type():
    """Unknown message type should produce a SystemMessage."""
    data = {"type": "unknown_type", "foo": "bar"}
    msg = parse_message(data)
    assert isinstance(msg, SystemMessage)
    assert msg.subtype == "unknown_type"
    assert msg.data["foo"] == "bar"


def test_parse_line_valid_json():
    """parse_line should parse a valid JSON line."""
    line = '{"type": "assistant", "message": {"content": [{"type": "text", "text": "hi"}]}}'
    msg = parse_line(line)
    assert msg is not None
    assert isinstance(msg, AssistantMessage)


def test_parse_line_invalid_json():
    """parse_line should return None for invalid JSON."""
    msg = parse_line("not json at all")
    assert msg is None


def test_parse_line_empty():
    """parse_line should return None for empty/whitespace lines."""
    assert parse_line("") is None
    assert parse_line("  ") is None
    assert parse_line("\n") is None
