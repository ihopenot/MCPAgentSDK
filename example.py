"""MCP Agent SDK usage examples.

Prerequisites:
    pip install mcp-agent-sdk
    Ensure `codebuddy` CLI is installed and available in PATH.
"""

import asyncio

from mcp_agent_sdk import (
    AgentProcessError,
    AgentResult,
    AgentRunConfig,
    AgentStartupError,
    AssistantMessage,
    ContentBlock,
    MCPAgentSDK,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)


def print_event(event: AssistantMessage | SystemMessage) -> None:
    """Pretty-print a stream event."""
    if isinstance(event, AssistantMessage):
        for block in event.content:
            if isinstance(block, TextBlock):
                print(f"  💬 {block.text}")
            elif isinstance(block, ThinkingBlock):
                print(f"  🧠 (thinking) {block.thinking[:200]}")
            elif isinstance(block, ToolUseBlock):
                print(f"  🔧 Tool: {block.name} {block.input}")
            elif isinstance(block, ToolResultBlock):
                prefix = "❌" if block.is_error else "✅"
                print(f"  {prefix} Result: {block.output[:200]}")
    elif isinstance(event, SystemMessage):
        # Only print meaningful system messages, skip noisy ones
        if event.subtype in ("init",):
            print(f"  ⚙️  Session started (model={event.data.get('model', '?')})")


# ---------------------------------------------------------------------------
# Example 1: Basic agent run (no validation)
# ---------------------------------------------------------------------------
async def basic_run() -> None:
    """Run an agent with a simple prompt and print streamed messages."""
    sdk = MCPAgentSDK()
    await sdk.init()

    config = AgentRunConfig(
        prompt="创建一个Team，a，b，c三个成员，每个成员创建自己名称.txt的文件，一定要创建team来完成，不要自己创建",
    )

    try:
        async for event in sdk.run_agent(config):
            if isinstance(event, AgentResult):
                print(f"\n✅ Done — status: {event.status}, message: {event.message}")
            else:
                print_event(event)
    except AgentStartupError as e:
        print(f"❌ Startup failed: {e}")
    except AgentProcessError as e:
        print(f"❌ Process crashed: {e}")

    await sdk.shutdown()


# ---------------------------------------------------------------------------
# Example 2: Validation with auto-retry
# ---------------------------------------------------------------------------
async def validated_run() -> None:
    """Run an agent with a custom validator that checks the result."""
    sdk = MCPAgentSDK()
    await sdk.init()

    def validate_result(result: str) -> tuple[bool, str]:
        """Return (True, '') on success, or (False, feedback) on failure."""
        if "hello" in result.lower():
            return (True, "")
        return (False, "Result must mention 'hello'. Please try again.")

    config = AgentRunConfig(
        prompt="Create a Python script that prints 'Hello from MCP Agent!'",
        validate_fn=validate_result,
        max_retries=3,
    )

    try:
        async for event in sdk.run_agent(config):
            if isinstance(event, AgentResult):
                print(f"\n✅ Done — status: {event.status}")
                print(f"   message: {event.message}")
            else:
                print_event(event)
    except (AgentStartupError, AgentProcessError) as e:
        print(f"❌ Error: {e}")

    await sdk.shutdown()


# ---------------------------------------------------------------------------
# Example 3: Callbacks + timeout
# ---------------------------------------------------------------------------
async def callback_run() -> None:
    """Run an agent with on_complete / on_block callbacks and a timeout."""
    sdk = MCPAgentSDK()
    await sdk.init()

    def on_complete(result: str) -> None:
        print(f"🎉 on_complete callback: {result}")

    def on_block(reason: str) -> None:
        print(f"🚧 on_block callback: {reason}")

    config = AgentRunConfig(
        prompt="List all Python files in the current directory",
        on_complete=on_complete,
        on_block=on_block,
        timeout=60.0,       # abort after 60 seconds
        max_retries=2,
    )

    try:
        async for event in sdk.run_agent(config):
            if isinstance(event, AgentResult):
                print(f"\nFinal: status={event.status}, message={event.message}")
            else:
                print_event(event)
    except (AgentStartupError, AgentProcessError) as e:
        print(f"❌ Error: {e}")

    await sdk.shutdown()


# ---------------------------------------------------------------------------
# Example 4: Running multiple agents concurrently
# ---------------------------------------------------------------------------
async def concurrent_runs() -> None:
    """Launch two agents at the same time; each gets its own run ID."""
    sdk = MCPAgentSDK()
    await sdk.init()

    async def _run(label: str, prompt: str) -> None:
        config = AgentRunConfig(prompt=prompt)
        try:
            async for event in sdk.run_agent(config):
                if isinstance(event, AgentResult):
                    print(f"[{label}] ✅ {event.status}: {event.message}")
                elif isinstance(event, AssistantMessage):
                    for block in event.content:
                        if isinstance(block, ToolUseBlock):
                            print(f"[{label}] 🔧 {block.name}")
        except (AgentStartupError, AgentProcessError) as e:
            print(f"[{label}] ❌ {e}")

    await asyncio.gather(
        _run("agent-1", "Create a file named a.txt with content 'A'"),
        _run("agent-2", "Create a file named b.txt with content 'B'"),
    )

    await sdk.shutdown()


# ---------------------------------------------------------------------------
# Example 5: Advanced configuration
# ---------------------------------------------------------------------------
async def advanced_run() -> None:
    """Demonstrate model selection, allowed tools, and extra CLI args."""
    sdk = MCPAgentSDK()
    await sdk.init()

    config = AgentRunConfig(
        prompt="Read the contents of pyproject.toml and summarize it",
        model="sonnet",
        allowed_tools=["Read", "Glob"],       # restrict available tools
        cwd=".",                              # working directory for the agent
        permission_mode="bypassPermissions",
        extra_args={"max-turns": "5"},        # limit conversation turns
    )

    try:
        async for event in sdk.run_agent(config):
            if isinstance(event, AgentResult):
                print(f"\n✅ Result: status={event.status}, message={event.message}")
            else:
                print_event(event)
    except (AgentStartupError, AgentProcessError) as e:
        print(f"❌ Error: {e}")

    await sdk.shutdown()


# ---------------------------------------------------------------------------
# Main — pick which example to run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    examples = {
        "basic": basic_run,
        "validated": validated_run,
        "callback": callback_run,
        "concurrent": concurrent_runs,
        "advanced": advanced_run,
    }

    name = sys.argv[1] if len(sys.argv) > 1 else "basic"
    if name not in examples:
        print(f"Usage: python example.py [{' | '.join(examples)}]")
        sys.exit(1)

    print(f"Running '{name}' example...\n")
    asyncio.run(examples[name]())
