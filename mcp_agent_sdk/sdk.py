"""MCPAgentSDK main class - orchestrates MCP server, subprocess, and validation."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator

from aiohttp import web

from mcp_agent_sdk.errors import AgentProcessError, AgentStartupError
from mcp_agent_sdk.mcp_server import _safe_call, create_mcp_app
from mcp_agent_sdk.message_parser import parse_line
from mcp_agent_sdk.process import (
    StderrReader,
    build_cli_args,
    find_codebuddy_cli,
    start_cli_process,
)
from mcp_agent_sdk.prompt_template import build_prompt
from mcp_agent_sdk.types import (
    AgentResult,
    AgentRunConfig,
    ResultMessage,
    RunContext,
    StreamEvent,
    SystemMessage,
)


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

    async def run_agent(self, config: AgentRunConfig) -> AsyncIterator[StreamEvent]:
        """Run an agent and yield structured events as they arrive.

        Launches a codebuddy subprocess with MCP config pointing to the
        internal server. The agent's Complete/Block tool calls are routed
        through the registry by agent_run_id.

        Args:
            config: Configuration for this agent run.

        Yields:
            StreamEvent subclasses: AssistantMessage, SystemMessage, AgentResult.
            ResultMessage is consumed internally for session_id extraction.

        Raises:
            AgentStartupError: If the process crashes before producing output.
            AgentProcessError: If the process exits without calling Complete/Block.
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

        # Start stderr reader
        stderr_reader = StderrReader(process.stderr)
        stderr_task = stderr_reader.start()

        session_id = ""
        status_changed = False
        stdout_lines_seen = False
        stdout_tail: list[str] = []

        def _make_agent_result() -> AgentResult:
            return AgentResult(
                status=ctx.status,
                message=ctx.result_message,
                session_id=session_id,
                agent_run_id=agent_run_id,
            )

        try:
            stdout = process.stdout  # type: ignore[union-attr]
            while True:
                # Race: read next line vs timeout-triggered status change
                read_task = asyncio.ensure_future(stdout.readline())
                try:
                    # Poll every 0.1s so we notice status changes from timeout
                    while not read_task.done():
                        if ctx.status != "running":
                            read_task.cancel()
                            break
                        await asyncio.sleep(0.1)
                    if ctx.status != "running":
                        process.terminate()
                        yield _make_agent_result()
                        status_changed = True
                        break
                    raw_line = read_task.result()
                except asyncio.CancelledError:
                    break

                if not raw_line:
                    # EOF — process closed stdout
                    break

                line = raw_line.decode("utf-8", errors="replace")
                stdout_lines_seen = True

                # Keep last 20 lines for diagnostics
                stdout_tail.append(line.rstrip())
                if len(stdout_tail) > 20:
                    stdout_tail.pop(0)

                event = parse_line(line)
                if event is None:
                    continue

                # Extract session_id from result/system messages but don't
                # yield ResultMessage — SDK synthesizes its own AgentResult.
                if isinstance(event, ResultMessage):
                    session_id = event.session_id or session_id
                elif isinstance(event, SystemMessage):
                    session_id = event.data.get("session_id", session_id)
                    yield event
                else:
                    yield event

                # Check if MCP handler changed the status
                if ctx.status != "running":
                    process.terminate()
                    yield _make_agent_result()
                    status_changed = True
                    break

            if not status_changed:
                # Process ended without Complete/Block being called
                await process.wait()
                # Wait for stderr reader to finish
                try:
                    await asyncio.wait_for(stderr_task, timeout=2)
                except asyncio.TimeoutError:
                    stderr_task.cancel()
                stderr_output = stderr_reader.get_output()
                exit_code = process.returncode

                if ctx.status == "running":
                    # Process exited abnormally
                    if not stdout_lines_seen:
                        raise AgentStartupError(
                            "Agent process crashed during startup",
                            stderr=stderr_output,
                            exit_code=exit_code,
                        )
                    else:
                        raise AgentProcessError(
                            "Agent process exited without calling Complete or Block",
                            stderr=stderr_output,
                            stdout_tail="\n".join(stdout_tail),
                            exit_code=exit_code,
                        )
                else:
                    # Status changed but process ended naturally
                    yield _make_agent_result()
        finally:
            # Clean up
            if timeout_task is not None:
                timeout_task.cancel()
            if not stderr_task.done():
                stderr_task.cancel()
            self._registry.pop(agent_run_id, None)
            # Ensure process is fully terminated and waited on, then close
            # pipe transports explicitly (prevents "unclosed transport"
            # ResourceWarning on Windows ProactorEventLoop).
            try:
                if process.returncode is None:
                    process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5)
            except (asyncio.TimeoutError, ProcessLookupError):
                process.kill()
                try:
                    await process.wait()
                except ProcessLookupError:
                    pass
            # Close pipe transports — on Windows these are
            # _ProactorBasePipeTransport objects that must be closed
            # explicitly to avoid ResourceWarning in __del__.
            for pipe in (process.stdout, process.stderr, process.stdin):
                if pipe is not None:
                    transport = getattr(pipe, "_transport", None) or getattr(pipe, "transport", None)
                    if transport is not None:
                        transport.close()
