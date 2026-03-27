# MCP Agent SDK

Python SDK for programmatically executing AI agent tasks with **automatic validation** and **human-in-the-loop** control.

## Features

- **Agent Execution** — Launch `codebuddy` CLI agents as managed subprocesses
- **Auto-Validation** — Validate task results with custom functions; failed validations trigger automatic retries
- **Human-in-the-Loop** — Agents can call `Block` to signal tasks that need human intervention
- **Structured Streaming** — Receive typed events (`AssistantMessage`, `SystemMessage`, `AgentResult`) via `AsyncIterator[StreamEvent]`
- **Error Diagnostics** — Process crashes raise specific exceptions with stderr capture and exit codes
- **Concurrent Agents** — Run multiple agents simultaneously, each tracked by a unique run ID
- **Timeout Support** — Set per-run timeouts that automatically block timed-out agents

## Installation

```bash
pip install mcp-agent-sdk
```

Or install from source:

```bash
git clone <repo-url>
cd MCPAgentSDK
pip install -e .
```

### Prerequisites

- Python ≥ 3.10
- `codebuddy` CLI installed and available in `PATH`

## Quick Start

```python
import asyncio
from mcp_agent_sdk import (
    MCPAgentSDK, AgentRunConfig, AgentResult,
    AssistantMessage, SystemMessage, TextBlock,
    AgentStartupError, AgentProcessError,
)

async def main():
    sdk = MCPAgentSDK()
    await sdk.init()

    config = AgentRunConfig(
        prompt="Create a file called hello.txt containing 'Hello, World!'",
    )

    try:
        async for event in sdk.run_agent(config):
            if isinstance(event, AgentResult):
                print(f"Done: {event.status} — {event.message}")
            elif isinstance(event, AssistantMessage):
                for block in event.content:
                    if isinstance(block, TextBlock):
                        print(f"[assistant] {block.text}")
            elif isinstance(event, SystemMessage):
                print(f"[system:{event.subtype}] {event.data}")
    except AgentStartupError as e:
        print(f"Startup failed: {e} (stderr={e.stderr}, exit_code={e.exit_code})")
    except AgentProcessError as e:
        print(f"Process crashed: {e} (stderr={e.stderr}, exit_code={e.exit_code})")

    await sdk.shutdown()

asyncio.run(main())
```

## API Reference

### `MCPAgentSDK`

The main entry point for running agents.

```python
sdk = MCPAgentSDK()
await sdk.init(host="127.0.0.1", port=0)  # port=0 auto-selects
```

| Property          | Type   | Description                          |
|-------------------|--------|--------------------------------------|
| `port`            | `int`  | Actual port the MCP server bound to  |
| `mcp_server_url`  | `str`  | Full URL of the MCP endpoint         |

| Method            | Description                                            |
|-------------------|--------------------------------------------------------|
| `init(host, port)`   | Start the internal MCP server                       |
| `shutdown()`         | Stop the server and clean up resources               |
| `run_agent(config)`  | Run an agent; returns `AsyncIterator[StreamEvent]`   |

### `AgentRunConfig`

Configuration dataclass for a single agent run.

```python
@dataclass
class AgentRunConfig:
    prompt: str                                                   # Task description
    validate_fn: Callable[[str], tuple[bool, str]] | None = None  # Custom validator
    on_complete: Callable[[str], None] | None = None              # Success callback
    on_block: Callable[[str], None] | None = None                 # Block callback
    max_retries: int = 3                                          # Validation retry limit
    model: str | None = None                                      # LLM model override
    permission_mode: str = "bypassPermissions"                    # CLI permission mode
    cwd: str | None = None                                        # Working directory
    allowed_tools: list[str] | None = None                        # Restrict agent tools
    extra_args: dict[str, str | None] = field(default_factory=dict)  # Extra CLI flags
    timeout: float | None = None                                  # Timeout in seconds
```

### Stream Event Types

`run_agent()` yields `StreamEvent` subclasses. Use `isinstance` to handle each type:

#### `AssistantMessage`

LLM response containing typed content blocks.

```python
@dataclass
class AssistantMessage(StreamEvent):
    content: list[ContentBlock]   # TextBlock, ThinkingBlock, ToolUseBlock, ToolResultBlock
    session_id: str = ""
```

#### `SystemMessage`

System events (init, cost, etc.).

```python
@dataclass
class SystemMessage(StreamEvent):
    subtype: str = ""             # "init", "cost", "error", etc.
    data: dict[str, Any] = {}
```

#### `ResultMessage`

Session-end metadata (consumed internally, not yielded).

```python
@dataclass
class ResultMessage(StreamEvent):
    session_id: str = ""
    cost_usd: float = 0.0
    duration_ms: int = 0
    is_error: bool = False
    num_turns: int = 0
```

#### `AgentResult`

Final result of an agent run.

```python
@dataclass
class AgentResult(StreamEvent):
    status: str = ""              # "completed" | "blocked"
    message: str = ""             # Result description
    session_id: str = ""
    agent_run_id: str = ""
    exit_code: int | None = None
    stderr_output: str = ""
```

### Content Block Types

Content blocks inside `AssistantMessage.content`:

| Type | Fields | Description |
|------|--------|-------------|
| `TextBlock` | `text: str` | Plain text response |
| `ThinkingBlock` | `thinking: str` | LLM internal reasoning |
| `ToolUseBlock` | `tool_use_id`, `name`, `input` | Agent requesting a tool call |
| `ToolResultBlock` | `tool_use_id`, `output`, `is_error` | Result from tool execution |

### Error Types

Process failures raise specific exceptions instead of yielding error events:

| Exception | When | Attributes |
|-----------|------|------------|
| `CLINotFoundError` | `codebuddy` not in PATH | — |
| `AgentStartupError` | Process crashes before producing output | `stderr`, `exit_code` |
| `AgentProcessError` | Process exits without calling Complete/Block | `stderr`, `stdout_tail`, `exit_code` |
| `AgentExecutionError` | Logical errors (auth failure, API error) | `errors`, `subtype` |

All inherit from `MCPAgentSDKError` (which inherits from `Exception`).

## Usage Patterns

### Validation with Auto-Retry

Provide a `validate_fn` to automatically verify results. If validation fails, the agent receives feedback and retries up to `max_retries` times.

```python
def validate(result: str) -> tuple[bool, str]:
    if "success" in result.lower():
        return (True, "")
    return (False, "Result must indicate success. Please fix and try again.")

config = AgentRunConfig(
    prompt="Create and test a hello-world script",
    validate_fn=validate,
    max_retries=3,
)
```

### Callbacks

Use `on_complete` and `on_block` for side effects when runs finish:

```python
config = AgentRunConfig(
    prompt="Deploy the staging environment",
    on_complete=lambda result: notify_slack(f"✅ Deploy done: {result}"),
    on_block=lambda reason: page_oncall(f"🚧 Deploy blocked: {reason}"),
)
```

### Timeout

Set a maximum duration. The agent is blocked automatically if it exceeds the limit:

```python
config = AgentRunConfig(
    prompt="Run the full test suite",
    timeout=120.0,  # 2 minutes
)
```

### Error Handling

Wrap `run_agent()` in try/except to catch process failures:

```python
from mcp_agent_sdk import AgentStartupError, AgentProcessError

try:
    async for event in sdk.run_agent(config):
        if isinstance(event, AgentResult):
            print(f"Result: {event.status}")
except AgentStartupError as e:
    print(f"CLI crashed on startup: {e}")
    print(f"stderr: {e.stderr}")
    print(f"exit code: {e.exit_code}")
except AgentProcessError as e:
    print(f"Agent died without completing: {e}")
    print(f"last output: {e.stdout_tail}")
```

### Concurrent Agents

Launch multiple agents in parallel — each gets its own isolated run context:

```python
async def run_all():
    sdk = MCPAgentSDK()
    await sdk.init()

    configs = [
        AgentRunConfig(prompt="Lint the codebase"),
        AgentRunConfig(prompt="Run unit tests"),
    ]

    async def _run(cfg):
        try:
            async for event in sdk.run_agent(cfg):
                if isinstance(event, AgentResult):
                    print(event.status)
        except (AgentStartupError, AgentProcessError) as e:
            print(f"Error: {e}")

    await asyncio.gather(*[_run(c) for c in configs])
    await sdk.shutdown()
```

## How It Works

```
Your Code ──► MCPAgentSDK.run_agent(config)
                │
                ├─ Start MCP HTTP server (JSON-RPC 2.0)
                ├─ Register RunContext with unique agent_run_id
                ├─ Inject system prompt with Complete/Block tool instructions
                ├─ Launch codebuddy subprocess with MCP config
                ├─ Start async stderr reader (deque buffer, last 100 lines)
                │
                │   ┌─────────────────────────────────────┐
                │   │  codebuddy agent runs task           │
                │   │  ├─ calls Complete(result) ──────────┼──► validate_fn() ──► retry or complete
                │   │  ├─ calls Block(reason)   ──────────┼──► on_block callback
                │   │  └─ crashes without calling either ──┼──► raise AgentProcessError(stderr)
                │   └─────────────────────────────────────┘
                │
                └─ Yield StreamEvent stream ──► your async for loop
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run unit tests
pytest

# Run end-to-end tests (requires codebuddy in PATH)
pytest -m e2e
```

## License

See [LICENSE](LICENSE) for details.
