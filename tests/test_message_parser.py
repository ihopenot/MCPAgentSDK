"""Tests for message parser: parse stdout JSON lines into Message objects."""

import pytest

from mcp_agent_sdk.message_parser import parse_message, parse_line


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
    assert msg.type == "assistant"
    assert msg.content["message"]["content"][0]["text"] == "Hello world"


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
    assert msg.type == "assistant"
    tool_block = msg.content["message"]["content"][0]
    assert tool_block["name"] == "Write"


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
    assert msg.type == "result"
    assert msg.content["session_id"] == "sess-abc"
    assert msg.content["is_error"] is False


def test_parse_system_message():
    """Parse a system message."""
    data = {
        "type": "system",
        "subtype": "init",
        "data": {"session_id": "sess-xyz"},
    }
    msg = parse_message(data)
    assert msg.type == "system"


def test_parse_error_message():
    """Parse an error message."""
    data = {
        "type": "error",
        "error": "something went wrong",
    }
    msg = parse_message(data)
    assert msg.type == "error"
    assert msg.content["error"] == "something went wrong"


def test_parse_unknown_type():
    """Unknown message type should still produce a Message."""
    data = {"type": "unknown_type", "foo": "bar"}
    msg = parse_message(data)
    assert msg.type == "unknown_type"
    assert msg.content["foo"] == "bar"


def test_parse_line_valid_json():
    """parse_line should parse a valid JSON line."""
    line = '{"type": "assistant", "message": {"content": [{"type": "text", "text": "hi"}]}}'
    msg = parse_line(line)
    assert msg is not None
    assert msg.type == "assistant"


def test_parse_line_invalid_json():
    """parse_line should return None for invalid JSON."""
    msg = parse_line("not json at all")
    assert msg is None


def test_parse_line_empty():
    """parse_line should return None for empty/whitespace lines."""
    assert parse_line("") is None
    assert parse_line("  ") is None
    assert parse_line("\n") is None
