"""Tests for error hierarchy in mcp_agent_sdk.errors."""

import pytest

from mcp_agent_sdk.errors import (
    MCPAgentSDKError,
    CLINotFoundError,
    AgentStartupError,
    AgentProcessError,
    AgentExecutionError,
)


class TestMCPAgentSDKError:
    """Base error class tests."""

    def test_is_exception(self):
        err = MCPAgentSDKError("base error")
        assert isinstance(err, Exception)
        assert str(err) == "base error"


class TestCLINotFoundError:
    """CLI not found error tests."""

    def test_inherits_base(self):
        err = CLINotFoundError("not found")
        assert isinstance(err, MCPAgentSDKError)
        assert str(err) == "not found"


class TestAgentStartupError:
    """Agent startup error tests."""

    def test_inherits_base(self):
        err = AgentStartupError("startup failed")
        assert isinstance(err, MCPAgentSDKError)

    def test_has_stderr_and_exit_code(self):
        err = AgentStartupError(
            "startup failed",
            stderr="Error: config not found\nFatal crash",
            exit_code=1,
        )
        assert str(err) == "startup failed"
        assert err.stderr == "Error: config not found\nFatal crash"
        assert err.exit_code == 1

    def test_defaults(self):
        err = AgentStartupError("fail")
        assert err.stderr == ""
        assert err.exit_code is None


class TestAgentProcessError:
    """Agent process error tests."""

    def test_inherits_base(self):
        err = AgentProcessError("process died")
        assert isinstance(err, MCPAgentSDKError)

    def test_has_stderr_stdout_tail_exit_code(self):
        err = AgentProcessError(
            "process died unexpectedly",
            stderr="segfault at 0x0",
            stdout_tail="last line of output",
            exit_code=139,
        )
        assert str(err) == "process died unexpectedly"
        assert err.stderr == "segfault at 0x0"
        assert err.stdout_tail == "last line of output"
        assert err.exit_code == 139

    def test_defaults(self):
        err = AgentProcessError("died")
        assert err.stderr == ""
        assert err.stdout_tail == ""
        assert err.exit_code is None


class TestAgentExecutionError:
    """Agent execution error tests."""

    def test_inherits_base(self):
        err = AgentExecutionError(errors=["auth failed"], subtype="authentication")
        assert isinstance(err, MCPAgentSDKError)

    def test_message_from_first_error(self):
        err = AgentExecutionError(
            errors=["first error", "second error"],
            subtype="api_error",
        )
        assert str(err) == "first error"
        assert err.errors == ["first error", "second error"]
        assert err.subtype == "api_error"

    def test_empty_errors_list(self):
        err = AgentExecutionError(errors=[], subtype="unknown")
        assert str(err) == "Execution failed"
        assert err.errors == []
        assert err.subtype == "unknown"
