"""Error hierarchy for MCP Agent SDK."""

from __future__ import annotations


class MCPAgentSDKError(Exception):
    """Base exception for all MCP Agent SDK errors."""

    pass


class CLINotFoundError(MCPAgentSDKError):
    """Raised when the codebuddy CLI executable is not found in PATH."""

    pass


class AgentStartupError(MCPAgentSDKError):
    """Raised when the agent process crashes during startup (before producing output)."""

    def __init__(self, message: str, stderr: str = "", exit_code: int | None = None):
        super().__init__(message)
        self.stderr = stderr
        self.exit_code = exit_code


class AgentProcessError(MCPAgentSDKError):
    """Raised when the agent process exits without calling Complete or Block."""

    def __init__(
        self,
        message: str,
        stderr: str = "",
        stdout_tail: str = "",
        exit_code: int | None = None,
    ):
        super().__init__(message)
        self.stderr = stderr
        self.stdout_tail = stdout_tail
        self.exit_code = exit_code


class AgentExecutionError(MCPAgentSDKError):
    """Raised on logical execution errors (authentication failure, API errors, etc.)."""

    def __init__(self, errors: list[str], subtype: str):
        message = errors[0] if errors else "Execution failed"
        super().__init__(message)
        self.errors = errors
        self.subtype = subtype
