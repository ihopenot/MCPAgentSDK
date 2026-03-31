"""Subprocess management for codebuddy CLI."""

from __future__ import annotations

import asyncio
import json
import shutil
from collections import deque
from typing import Any

from mcp_agent_sdk.errors import CLINotFoundError
from mcp_agent_sdk.types import AgentRunConfig

# Buffer limit for subprocess streams (100 MB)
_STREAM_BUFFER_LIMIT = 100 * 1024 * 1024


def build_cli_args(
    config: AgentRunConfig,
    full_prompt: str,
    mcp_server_url: str,
) -> list[str]:
    """Build CLI arguments for the codebuddy subprocess.

    The prompt is sent via stdin, not included in args.
    """
    args = [
        "--input-format=stream-json",
        "--output-format=stream-json",
        "--verbose",
        "--print",
    ]

    # Permission mode
    args.extend(["--permission-mode", config.permission_mode])

    # Model
    if config.model:
        args.extend(["--model", config.model])

    # Allowed tools
    if config.allowed_tools:
        args.extend(["--allowedTools"] + list(config.allowed_tools))

    # MCP config - inject our server, merge with user-provided servers
    mcp_servers = dict(config.mcp_servers)  # shallow copy
    # Ensure built-in agent-controller is never overwritten
    mcp_servers["agent-controller"] = {
        "type": "http",
        "url": mcp_server_url,
    }
    mcp_config = {"mcpServers": mcp_servers}
    args.extend(["--mcp-config", json.dumps(mcp_config)])

    # Isolation: don't load filesystem settings
    args.extend(["--setting-sources", "none"])

    # Extra args
    for flag, value in config.extra_args.items():
        if value is None:
            args.append(f"--{flag}")
        else:
            args.extend([f"--{flag}", value])

    return args


def find_codebuddy_cli() -> str:
    """Find the codebuddy CLI binary in PATH.

    Returns the path to the binary.
    Raises FileNotFoundError if not found.
    """
    path = shutil.which("codebuddy")
    if path is None:
        raise CLINotFoundError(
            "codebuddy CLI not found in PATH. "
            "Please ensure codebuddy is installed and available."
        )
    return path


async def start_cli_process(
    cli_path: str,
    args: list[str],
    full_prompt: str,
    cwd: str | None = None,
) -> asyncio.subprocess.Process:
    """Start the codebuddy CLI subprocess.

    Sends the prompt via stdin as a stream-json message.
    """
    process = await asyncio.create_subprocess_exec(
        cli_path, *args,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
        limit=_STREAM_BUFFER_LIMIT,
    )

    # Send prompt via stdin in stream-json format (keep stdin open so
    # the CLI stays alive waiting for more input / MCP interactions).
    prompt_message = json.dumps({
        "type": "user",
        "message": {
            "content": [{"type": "text", "text": full_prompt}],
            "role": "user",
        }
    })
    if process.stdin:
        process.stdin.write((prompt_message + "\n").encode())
        await process.stdin.drain()
        # NOTE: Do NOT close stdin here. Closing stdin signals EOF to the
        # CLI, causing it to exit after the current turn — before the agent
        # has a chance to call Complete/Block via MCP.

    return process


class StderrReader:
    """Asynchronously reads stderr lines into a bounded deque buffer."""

    def __init__(self, stderr_stream: Any, maxlen: int = 100) -> None:
        self._stream = stderr_stream
        self._lines: deque[str] = deque(maxlen=maxlen)

    def start(self) -> asyncio.Task[None]:
        """Start the background reader task. Returns the task."""
        return asyncio.create_task(self._read_loop())

    async def _read_loop(self) -> None:
        """Read lines from stderr until EOF."""
        while True:
            raw = await self._stream.readline()
            if not raw:
                break
            line = raw.decode("utf-8", errors="replace").rstrip("\n").rstrip("\r")
            if line:
                self._lines.append(line)

    def get_lines(self) -> list[str]:
        """Return buffered stderr lines as a list."""
        return list(self._lines)

    def get_output(self) -> str:
        """Return buffered stderr as a single string joined by newlines."""
        return "\n".join(self._lines)
