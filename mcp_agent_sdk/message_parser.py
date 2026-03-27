"""Parse codebuddy CLI stdout JSON stream into structured types."""

from __future__ import annotations

import json
from typing import Any

from mcp_agent_sdk.types import (
    AssistantMessage,
    ContentBlock,
    ResultMessage,
    StreamEvent,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)


def _parse_content_block(block: dict[str, Any]) -> ContentBlock:
    """Parse a single content block dict into a typed ContentBlock."""
    block_type = block.get("type", "unknown")

    if block_type == "text":
        return TextBlock(text=block.get("text", ""))
    elif block_type == "thinking":
        return ThinkingBlock(thinking=block.get("thinking", ""))
    elif block_type == "tool_use":
        return ToolUseBlock(
            tool_use_id=block.get("id", ""),
            name=block.get("name", ""),
            input=block.get("input", {}),
        )
    elif block_type == "tool_result":
        return ToolResultBlock(
            tool_use_id=block.get("tool_use_id", ""),
            output=block.get("output", ""),
            is_error=block.get("is_error", False),
        )
    else:
        # Unknown block type — preserve as generic ContentBlock
        return ContentBlock(type=block_type)


def _parse_assistant(data: dict[str, Any]) -> AssistantMessage:
    """Parse an assistant message."""
    message = data.get("message", {})
    raw_blocks = message.get("content", [])
    content = [_parse_content_block(b) for b in raw_blocks]
    return AssistantMessage(content=content)


def _parse_system(data: dict[str, Any]) -> SystemMessage:
    """Parse a system message."""
    subtype = data.get("subtype", "system")
    # Include everything except 'type' in data
    msg_data = {k: v for k, v in data.items() if k != "type"}
    return SystemMessage(subtype=subtype, data=msg_data)


def _parse_result(data: dict[str, Any]) -> ResultMessage:
    """Parse a result message."""
    return ResultMessage(
        session_id=data.get("session_id", ""),
        cost_usd=data.get("cost_usd", 0.0),
        duration_ms=data.get("duration_ms", 0),
        is_error=data.get("is_error", False),
        num_turns=data.get("num_turns", 0),
    )


def parse_message(data: dict[str, Any]) -> StreamEvent:
    """Parse a raw JSON dict into a structured StreamEvent type."""
    msg_type = data.get("type", "unknown")

    if msg_type == "assistant":
        return _parse_assistant(data)
    elif msg_type == "system":
        return _parse_system(data)
    elif msg_type == "result":
        return _parse_result(data)
    else:
        # Unknown type (including "error") — wrap as SystemMessage
        subtype = msg_type if msg_type != "unknown" else "unknown"
        msg_data = {k: v for k, v in data.items() if k != "type"}
        return SystemMessage(subtype=subtype, data=msg_data)


def parse_line(line: str) -> StreamEvent | None:
    """Parse a single JSON line from stdout into a structured type.

    Returns None for empty lines or invalid JSON.
    """
    stripped = line.strip()
    if not stripped:
        return None
    try:
        data = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return parse_message(data)
