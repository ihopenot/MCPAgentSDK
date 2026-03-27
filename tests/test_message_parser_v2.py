"""Tests for message parser returning structured types instead of raw Message."""

import pytest

from mcp_agent_sdk.types import (
    AssistantMessage,
    ContentBlock,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)
from mcp_agent_sdk.message_parser import parse_line, parse_message


class TestParseAssistant:
    """Assistant messages should become AssistantMessage with typed ContentBlocks."""

    def test_text_content(self):
        data = {
            "type": "assistant",
            "message": {
                "content": [{"type": "text", "text": "Hello world"}]
            },
        }
        msg = parse_message(data)
        assert isinstance(msg, AssistantMessage)
        assert len(msg.content) == 1
        assert isinstance(msg.content[0], TextBlock)
        assert msg.content[0].text == "Hello world"

    def test_tool_use_content(self):
        data = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "id": "tu_1", "name": "Write", "input": {"path": "x.py"}}
                ]
            },
        }
        msg = parse_message(data)
        assert isinstance(msg, AssistantMessage)
        block = msg.content[0]
        assert isinstance(block, ToolUseBlock)
        assert block.tool_use_id == "tu_1"
        assert block.name == "Write"
        assert block.input == {"path": "x.py"}

    def test_thinking_content(self):
        data = {
            "type": "assistant",
            "message": {
                "content": [{"type": "thinking", "thinking": "let me think"}]
            },
        }
        msg = parse_message(data)
        assert isinstance(msg, AssistantMessage)
        block = msg.content[0]
        assert isinstance(block, ThinkingBlock)
        assert block.thinking == "let me think"

    def test_tool_result_content(self):
        data = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_result", "tool_use_id": "tu_1", "output": "done", "is_error": False}
                ]
            },
        }
        msg = parse_message(data)
        assert isinstance(msg, AssistantMessage)
        block = msg.content[0]
        assert isinstance(block, ToolResultBlock)
        assert block.tool_use_id == "tu_1"
        assert block.output == "done"
        assert block.is_error is False

    def test_mixed_content(self):
        data = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "thinking", "thinking": "hmm"},
                    {"type": "text", "text": "answer"},
                    {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"cmd": "ls"}},
                ]
            },
        }
        msg = parse_message(data)
        assert isinstance(msg, AssistantMessage)
        assert len(msg.content) == 3
        assert isinstance(msg.content[0], ThinkingBlock)
        assert isinstance(msg.content[1], TextBlock)
        assert isinstance(msg.content[2], ToolUseBlock)

    def test_unknown_content_block_type(self):
        """Unknown block types should become generic ContentBlock."""
        data = {
            "type": "assistant",
            "message": {
                "content": [{"type": "image", "url": "http://example.com/img.png"}]
            },
        }
        msg = parse_message(data)
        assert isinstance(msg, AssistantMessage)
        assert len(msg.content) == 1
        block = msg.content[0]
        assert isinstance(block, ContentBlock)
        assert block.type == "image"


class TestParseSystem:
    """System messages should become SystemMessage."""

    def test_system_message(self):
        data = {
            "type": "system",
            "subtype": "init",
            "session_id": "sess-xyz",
        }
        msg = parse_message(data)
        assert isinstance(msg, SystemMessage)
        assert msg.subtype == "init"
        # data should contain the full original dict minus 'type'
        assert "session_id" in msg.data


class TestParseResult:
    """Result messages should become ResultMessage."""

    def test_result_message(self):
        data = {
            "type": "result",
            "session_id": "sess-abc",
            "is_error": False,
            "num_turns": 5,
            "duration_ms": 12000,
            "cost_usd": 0.03,
        }
        msg = parse_message(data)
        assert isinstance(msg, ResultMessage)
        assert msg.session_id == "sess-abc"
        assert msg.is_error is False
        assert msg.num_turns == 5
        assert msg.duration_ms == 12000
        assert msg.cost_usd == 0.03

    def test_result_message_minimal(self):
        data = {"type": "result", "session_id": "s1"}
        msg = parse_message(data)
        assert isinstance(msg, ResultMessage)
        assert msg.session_id == "s1"
        assert msg.cost_usd == 0.0


class TestParseUnknown:
    """Unknown types should become SystemMessage(subtype='unknown')."""

    def test_unknown_type(self):
        data = {"type": "foobar", "key": "value"}
        msg = parse_message(data)
        assert isinstance(msg, SystemMessage)
        assert msg.subtype == "foobar"
        assert msg.data["key"] == "value"

    def test_error_type(self):
        data = {"type": "error", "error": "something broke"}
        msg = parse_message(data)
        assert isinstance(msg, SystemMessage)
        assert msg.subtype == "error"
        assert msg.data["error"] == "something broke"


class TestParseLine:
    """parse_line should work with the new types."""

    def test_valid_json(self):
        line = '{"type": "assistant", "message": {"content": [{"type": "text", "text": "hi"}]}}'
        msg = parse_line(line)
        assert msg is not None
        assert isinstance(msg, AssistantMessage)

    def test_invalid_json(self):
        assert parse_line("not json") is None

    def test_empty_line(self):
        assert parse_line("") is None
        assert parse_line("  ") is None
