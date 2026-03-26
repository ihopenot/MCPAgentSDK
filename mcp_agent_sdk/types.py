from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


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
class AgentResult:
    """Structured result returned when an agent run finishes."""

    status: str  # "completed" | "blocked" | "error"
    message: str
    session_id: str
    agent_run_id: str


@dataclass
class Message:
    """A single message from the codebuddy CLI stdout stream."""

    type: str  # "assistant" | "tool_use" | "tool_result" | "system" | "result" | "error"
    content: dict[str, Any] = field(default_factory=dict)


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
