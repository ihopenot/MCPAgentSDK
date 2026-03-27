from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# StreamEvent base — all types yielded by run_agent() inherit from this
# ---------------------------------------------------------------------------

@dataclass
class StreamEvent:
    """Abstract base for all events yielded by run_agent()."""
    pass


# ---------------------------------------------------------------------------
# ContentBlock hierarchy — building blocks inside AssistantMessage
# ---------------------------------------------------------------------------

@dataclass
class ContentBlock:
    """Base class for content blocks inside an AssistantMessage."""
    type: str


@dataclass
class TextBlock(ContentBlock):
    """Plain text content."""
    text: str
    type: str = field(default="text", init=False)


@dataclass
class ThinkingBlock(ContentBlock):
    """LLM internal reasoning."""
    thinking: str
    type: str = field(default="thinking", init=False)


@dataclass
class ToolUseBlock(ContentBlock):
    """Agent requesting a tool call."""
    tool_use_id: str
    name: str
    input: dict[str, Any]
    type: str = field(default="tool_use", init=False)


@dataclass
class ToolResultBlock(ContentBlock):
    """Result from a tool execution."""
    tool_use_id: str
    output: str
    is_error: bool = False
    type: str = field(default="tool_result", init=False)


# ---------------------------------------------------------------------------
# Message types — concrete StreamEvent subclasses
# ---------------------------------------------------------------------------

@dataclass
class AssistantMessage(StreamEvent):
    """LLM response containing text, thinking, or tool-use blocks."""
    content: list[ContentBlock] = field(default_factory=list)
    session_id: str = ""


@dataclass
class SystemMessage(StreamEvent):
    """System event (init, cost, etc.)."""
    subtype: str = ""
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResultMessage(StreamEvent):
    """Session-end metadata."""
    session_id: str = ""
    cost_usd: float = 0.0
    duration_ms: int = 0
    is_error: bool = False
    num_turns: int = 0


@dataclass
class AgentResult(StreamEvent):
    """Final result of an agent run."""
    status: str = ""        # "completed" | "blocked"
    message: str = ""
    session_id: str = ""
    agent_run_id: str = ""
    exit_code: int | None = None
    stderr_output: str = ""


# ---------------------------------------------------------------------------
# Internal / config types (unchanged from original)
# ---------------------------------------------------------------------------

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
    extra_args: dict[str, str | None] = field(default_factory=dict)
    timeout: float | None = None


@dataclass
class RunContext:
    """Internal registry entry tracking a single agent run."""

    validate_fn: Callable[[str], tuple[bool, str]] | None
    on_complete: Callable[[str], None] | None
    on_block: Callable[[str], None] | None
    max_retries: int
    retry_count: int = 0
    status: str = "running"  # "running" | "completed" | "blocked"
    result_message: str = ""
