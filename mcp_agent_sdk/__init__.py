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
    CanUseTool,
    CanUseToolOptions,
    ContentBlock,
    HookCallback,
    HookContext,
    HookEvent,
    HookJSONOutput,
    HookMatcher,
    PermissionResult,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    RunContext,
    StreamEvent,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    default_deny_can_use_tool,
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
    # can_use_tool types
    "CanUseTool",
    "CanUseToolOptions",
    "PermissionResult",
    "PermissionResultAllow",
    "PermissionResultDeny",
    "default_deny_can_use_tool",
]


def __getattr__(name: str):
    if name == "MCPAgentSDK":
        from mcp_agent_sdk.sdk import MCPAgentSDK

        return MCPAgentSDK
    raise AttributeError(f"module 'mcp_agent_sdk' has no attribute {name!r}")
