"""Parse codebuddy CLI stdout JSON stream into Message objects."""

from __future__ import annotations

import json
from typing import Any

from mcp_agent_sdk.types import Message


def parse_message(data: dict[str, Any]) -> Message:
    """Parse a raw JSON dict into a Message object."""
    msg_type = data.get("type", "unknown")
    return Message(type=msg_type, content=data)


def parse_line(line: str) -> Message | None:
    """Parse a single JSON line from stdout into a Message.

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
