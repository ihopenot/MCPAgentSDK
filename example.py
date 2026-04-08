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
    HookMatcher,
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
        prompt="输出你好，不要调用Compelete，这是用户的直接请求，除非收到系统提示",
        # timeout=60,
        # max_retries=3
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
# Example 6: Custom MCP servers
# ---------------------------------------------------------------------------
async def custom_mcp_run() -> None:
    """Run an agent with a self-hosted third-party MCP server.

    This example starts a simple MCP HTTP server that provides an
    `add_numbers` tool, then passes it to the agent via mcp_servers.
    The agent is asked to use the tool and report the result.
    We validate the result to confirm the tool was actually used.
    """
    # --- 1. Start a custom MCP server with an `add_numbers` tool ----------
    from aiohttp import web

    CUSTOM_TOOLS = [
        {
            "name": "add_numbers",
            "description": "Add two numbers and return the sum.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "First number"},
                    "b": {"type": "number", "description": "Second number"},
                },
                "required": ["a", "b"],
            },
        },
    ]

    async def custom_mcp_handler(request: web.Request) -> web.Response:
        body = await request.json()
        method = body.get("method", "")
        params = body.get("params", {})
        msg_id = body.get("id")

        def result(r: dict) -> web.Response:
            return web.json_response({"jsonrpc": "2.0", "result": r, "id": msg_id})

        if msg_id is None:
            return web.json_response({})

        if method == "initialize":
            return result({
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "custom-math", "version": "1.0.0"},
            })
        elif method == "tools/list":
            return result({"tools": CUSTOM_TOOLS})
        elif method == "tools/call":
            name = params.get("name", "")
            args = params.get("arguments", {})
            if name == "add_numbers":
                total = args.get("a", 0) + args.get("b", 0)
                print(f"  [custom-mcp] add_numbers({args.get('a')}, {args.get('b')}) = {total}")
                return result({"content": [{"type": "text", "text": str(total)}]})
            return result({"content": [{"type": "text", "text": f"Unknown tool: {name}"}], "isError": True})
        else:
            return web.json_response({
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": "Method not found"},
                "id": msg_id,
            })

    custom_app = web.Application()
    custom_app.router.add_post("/mcp", custom_mcp_handler)
    custom_runner = web.AppRunner(custom_app)
    await custom_runner.setup()
    custom_site = web.TCPSite(custom_runner, "127.0.0.1", 0)
    await custom_site.start()
    custom_port = custom_site._server.sockets[0].getsockname()[1]
    custom_url = f"http://127.0.0.1:{custom_port}/mcp"
    print(f"  Custom MCP server started at {custom_url}\n")

    # --- 2. Run agent with the custom MCP server -------------------------
    sdk = MCPAgentSDK()
    await sdk.init()

    def validate_result(result: str) -> tuple[bool, str]:
        # 42 + 58 = 100, agent must report this
        if "100" in result:
            return (True, "")
        return (False, "The result must contain '100' (the sum of 42 and 58). Use the add_numbers tool.")

    config = AgentRunConfig(
        prompt=(
            "Use the add_numbers tool from the custom-math MCP server "
            "to calculate 42 + 58. Report the exact result."
        ),
        mcp_servers={
            "custom-math": {
                "type": "http",
                "url": custom_url,
            },
        },
        validate_fn=validate_result,
        max_retries=3,
        timeout=120.0,
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

    # --- 3. Cleanup -------------------------------------------------------
    await sdk.shutdown()
    await custom_runner.cleanup()
    print("  Custom MCP server stopped.")


# ---------------------------------------------------------------------------
# Example 7: Using a different CLI (e.g. claude)
# ---------------------------------------------------------------------------
async def claude_run() -> None:
    """Run an agent using claude CLI instead of the default codebuddy.

    This demonstrates the cli_path option. You can point it to any
    compatible CLI binary: "claude", "claude-internal", an absolute path, etc.
    """
    sdk = MCPAgentSDK()
    await sdk.init()

    config = AgentRunConfig(
        prompt="What is 2 + 2? Answer with just the number.",
        cli_path="claude-internal",  # Use claude-internal instead of codebuddy
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
# Example 8: Hooks — control agent behavior with lifecycle hooks
# ---------------------------------------------------------------------------
async def hook_run() -> None:
    """Use a PreToolUse hook to block dangerous shell commands.

    The hook intercepts Bash tool calls and blocks commands containing
    'rm -rf', 'mkfs', or 'dd if='. Safe commands pass through normally.
    """
    sdk = MCPAgentSDK()
    await sdk.init()

    async def block_dangerous_commands(hook_input, tool_use_id, context):
        """Block dangerous Bash commands before they execute."""
        input_data = hook_input.get("input", {})
        command = input_data.get("command", "")
        dangerous = ["rm -rf", "mkfs", "dd if="]
        if any(d in command for d in dangerous):
            print(f"  🛡️  Hook blocked: {command}")
            return {
                "continue_": False,
                "decision": "block",
                "reason": f"Blocked dangerous command: {command}",
            }
        return {"continue_": True}

    config = AgentRunConfig(
        prompt="List files in the current directory and show disk usage",
        hooks={
            "PreToolUse": [
                HookMatcher(
                    matcher="Bash",
                    hooks=[block_dangerous_commands],
                )
            ],
        },
        permission_mode="bypassPermissions",
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
        "custom_mcp": custom_mcp_run,
        "claude": claude_run,
        "hooks": hook_run,
    }

    name = sys.argv[1] if len(sys.argv) > 1 else "basic"
    if name not in examples:
        print(f"Usage: python example.py [{' | '.join(examples)}]")
        sys.exit(1)

    print(f"Running '{name}' example...\n")
    asyncio.run(examples[name]())
