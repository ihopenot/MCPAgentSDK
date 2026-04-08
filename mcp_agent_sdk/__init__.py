"""MCP Agent SDK - Agent execution with auto-validation via MCP tools."""

from mcp_agent_sdk.errors import (
    AgentExecutionError,
    AgentProcessError,
    AgentStartupError,
    CLINotFoundError,
    MCPAgentSDKError,
)
from mcp_agent_sdk.types import (
    AgentResult,
    AgentRunConfig,
    AssistantMessage,
    ContentBlock,
    HookCallback,
    HookContext,
    HookEvent,
    HookJSONOutput,
    HookMatcher,
    ResultMessage,
    RunContext,
    StreamEvent,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)

__all__ = [
    # Errors
    "AgentExecutionError",
    "AgentProcessError",
    "AgentStartupError",
    "CLINotFoundError",
    "MCPAgentSDKError",
    # Types
    "AgentResult",
    "AgentRunConfig",
    "AssistantMessage",
    "ContentBlock",
    "MCPAgentSDK",
    "ResultMessage",
    "RunContext",
    "StreamEvent",
    "SystemMessage",
    "TextBlock",
    "ThinkingBlock",
    "ToolResultBlock",
    "ToolUseBlock",
    # Hook types
    "HookCallback",
    "HookContext",
    "HookEvent",
    "HookJSONOutput",
    "HookMatcher",
]


def __getattr__(name: str):
    if name == "MCPAgentSDK":
        from mcp_agent_sdk.sdk import MCPAgentSDK

        return MCPAgentSDK
    raise AttributeError(f"module 'mcp_agent_sdk' has no attribute {name!r}")
