"""MCP Agent SDK - Agent execution with auto-validation via MCP tools."""

from mcp_agent_sdk.types import AgentResult, AgentRunConfig, Message, RunContext

__all__ = [
    "AgentResult",
    "AgentRunConfig",
    "MCPAgentSDK",
    "Message",
    "RunContext",
]


def __getattr__(name: str):
    if name == "MCPAgentSDK":
        from mcp_agent_sdk.sdk import MCPAgentSDK

        return MCPAgentSDK
    raise AttributeError(f"module 'mcp_agent_sdk' has no attribute {name!r}")
