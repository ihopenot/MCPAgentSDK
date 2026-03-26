"""MCPAgentSDK main class - orchestrates MCP server, subprocess, and validation."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from typing import Any

from aiohttp import web

from mcp_agent_sdk.mcp_server import _safe_call, create_mcp_app
from mcp_agent_sdk.message_parser import parse_line
from mcp_agent_sdk.process import build_cli_args, find_codebuddy_cli, start_cli_process
from mcp_agent_sdk.prompt_template import build_prompt
from mcp_agent_sdk.types import AgentRunConfig, Message, RunContext


class MCPAgentSDK:
    """Agent SDK with MCP-based auto-validation and human-in-the-loop control."""

    def __init__(self) -> None:
        self._registry: dict[str, RunContext] = {}
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None
        self._host: str = "127.0.0.1"
        self._port: int = 0

    @property
    def port(self) -> int:
        """The actual port the MCP server is listening on."""
        return self._port

    @property
    def mcp_server_url(self) -> str:
        """The full URL for the MCP server endpoint."""
        return f"http://{self._host}:{self._port}/mcp"

    async def init(self, host: str = "127.0.0.1", port: int = 0) -> None:
        """Start the MCP Streamable HTTP server.

        Args:
            host: Host to bind to. Defaults to 127.0.0.1.
            port: Port to bind to. 0 means auto-select an available port.
        """
        # Clean up previous server if init() called without shutdown()
        if self._runner is not None:
            await self.shutdown()

        self._host = host
        self._registry.clear()

        self._app = create_mcp_app(self._registry)
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, host, port)
        await self._site.start()

        # Resolve actual port if port=0
        sockets = self._site._server.sockets  # type: ignore[union-attr]
        if sockets:
            self._port = sockets[0].getsockname()[1]
        else:
            self._port = port

    async def shutdown(self) -> None:
        """Stop the MCP server and clean up all resources."""
        self._registry.clear()
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
        self._app = None
        self._site = None
        self._port = 0

    async def run_agent(self, config: AgentRunConfig) -> AsyncIterator[Message]:
        """Run an agent and yield messages as they arrive.

        Launches a codebuddy subprocess with MCP config pointing to the
        internal server. The agent's Complete/Block tool calls are routed
        through the registry by agent_run_id.

        Args:
            config: Configuration for this agent run.

        Yields:
            Message objects from the agent's stdout stream.
            The final message has type="agent_result" with the AgentResult data.
            Raw CLI "result" messages are consumed internally (for session_id
            extraction) but not yielded, to avoid ambiguity.
        """
        if self._port == 0:
            raise RuntimeError("SDK not initialized. Call await sdk.init() first.")

        # Generate unique run ID
        agent_run_id = uuid.uuid4().hex[:8]

        # Register in registry
        ctx = RunContext(
            validate_fn=config.validate_fn,
            on_complete=config.on_complete,
            on_block=config.on_block,
            max_retries=config.max_retries,
        )
        self._registry[agent_run_id] = ctx

        # Build prompt with system instructions
        full_prompt = build_prompt(agent_run_id, config.prompt)

        # Build CLI args
        cli_path = find_codebuddy_cli()
        args = build_cli_args(config, full_prompt, self.mcp_server_url)

        # Start subprocess
        process = await start_cli_process(
            cli_path=cli_path,
            args=args,
            full_prompt=full_prompt,
            cwd=config.cwd,
        )

        # Schedule timeout if configured
        timeout_task: asyncio.Task | None = None
        if config.timeout is not None and config.timeout > 0:
            async def _timeout_trigger() -> None:
                await asyncio.sleep(config.timeout)
                if ctx.status == "running":
                    ctx.status = "blocked"
                    ctx.result_message = (
                        f"Agent run timed out after {config.timeout}s"
                    )
                    await _safe_call(ctx.on_block, ctx.result_message)

            timeout_task = asyncio.create_task(_timeout_trigger())

        session_id = ""
        status_changed = False
        try:
            stdout = process.stdout  # type: ignore[union-attr]
            while True:
                # Race: read next line vs timeout-triggered status change
                read_task = asyncio.ensure_future(stdout.readline())
                try:
                    # Poll every 0.5s so we notice status changes from timeout
                    while not read_task.done():
                        if ctx.status != "running":
                            read_task.cancel()
                            break
                        await asyncio.sleep(0.1)
                    if ctx.status != "running":
                        process.terminate()
                        yield Message(
                            type="agent_result",
                            content={
                                "status": ctx.status,
                                "message": ctx.result_message,
                                "session_id": session_id,
                                "agent_run_id": agent_run_id,
                            },
                        )
                        status_changed = True
                        break
                    raw_line = read_task.result()
                except asyncio.CancelledError:
                    break

                if not raw_line:
                    # EOF — process closed stdout
                    break

                line = raw_line.decode("utf-8", errors="replace")
                msg = parse_line(line)
                if msg is None:
                    continue

                # Extract session_id from result/system messages but don't
                # yield raw CLI result messages to avoid duplicate results.
                if msg.type == "result":
                    session_id = msg.content.get("session_id", session_id)
                    # Don't yield — SDK will synthesize its own agent_result
                elif msg.type == "system":
                    session_id = msg.content.get("session_id", session_id)
                    yield msg
                else:
                    yield msg

                # Check if MCP handler changed the status
                if ctx.status != "running":
                    process.terminate()
                    yield Message(
                        type="agent_result",
                        content={
                            "status": ctx.status,
                            "message": ctx.result_message,
                            "session_id": session_id,
                            "agent_run_id": agent_run_id,
                        },
                    )
                    status_changed = True
                    break

            if not status_changed:
                # Process ended without Complete/Block being called
                await process.wait()
                if ctx.status == "running":
                    yield Message(
                        type="agent_result",
                        content={
                            "status": "error",
                            "message": "Agent process exited without calling Complete or Block",
                            "session_id": session_id,
                            "agent_run_id": agent_run_id,
                        },
                    )
                else:
                    # Status changed but process ended naturally
                    yield Message(
                        type="agent_result",
                        content={
                            "status": ctx.status,
                            "message": ctx.result_message,
                            "session_id": session_id,
                            "agent_run_id": agent_run_id,
                        },
                    )
        finally:
            # Clean up
            if timeout_task is not None:
                timeout_task.cancel()
            self._registry.pop(agent_run_id, None)
            if process.returncode is None:
                try:
                    process.terminate()
                    await asyncio.wait_for(process.wait(), timeout=5)
                except (asyncio.TimeoutError, ProcessLookupError):
                    process.kill()
