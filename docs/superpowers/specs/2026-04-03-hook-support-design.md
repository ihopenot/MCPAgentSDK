# Hook Support for MCPAgentSDK

**Date:** 2026-04-03
**Status:** Approved
**Scope:** Add Hook lifecycle support to MCPAgentSDK, aligned with the native codebuddy_agent_sdk implementation

---

## Overview

Add a Hook system to MCPAgentSDK that allows users to intercept and control agent behavior at key lifecycle points. The implementation follows the native codebuddy_agent_sdk's control protocol pattern and supports all 6 hook events.

### Goal

- Support all 6 hook events: `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop`, `SubagentStop`, `PreCompact`
- Use stdin/stdout control protocol for hook communication (matching native SDK)
- Preserve existing MCP HTTP architecture for Complete/Block (zero impact on current functionality)
- Provide a practical example demonstrating PreToolUse hook usage

---

## Architecture

### Communication Model (Hybrid)

```
SDK ←→ CLI Communication:

1. MCP HTTP Server (existing, unchanged):
   CLI → HTTP POST → SDK's MCP server → Complete/Block handling

2. Control Protocol (new, for hooks):
   SDK → stdin → CLI:  initialize request (hooks config)
   CLI → stdout → SDK: hook_callback control_request
   SDK → stdin → CLI:  control_response (hook result)
```

The hybrid approach keeps existing Complete/Block functionality entirely untouched while adding Hook support through the control protocol that the CLI already understands.

---

## Type Definitions

All new types go in `types.py`.

### HookEvent

```python
HookEvent = Literal[
    "PreToolUse", "PostToolUse", "UserPromptSubmit",
    "Stop", "SubagentStop", "PreCompact"
]
```

### HookContext

```python
class HookContext(TypedDict):
    signal: Any | None
```

### HookJSONOutput (Hook callback return value)

```python
class HookJSONOutput(TypedDict, total=False):
    continue_: bool           # Whether to continue execution
    suppressOutput: bool      # Whether to suppress output
    stopReason: str           # Reason for stopping
    decision: str             # Decision type (e.g., "block")
    reason: str               # Decision reason
```

Note: `continue_` uses trailing underscore to avoid Python keyword conflict. The SDK maps it to `continue` in the JSON protocol.

### HookCallback

```python
HookCallback = Callable[
    [Any, str | None, HookContext],
    Awaitable[HookJSONOutput],
]
```

All hook callbacks must be async functions. Parameters:
- `hook_input`: The input data from the CLI (tool name, args, etc.)
- `tool_use_id`: The tool use ID (if applicable, None otherwise)
- `context`: HookContext with signal for cancellation

### HookMatcher

```python
@dataclass
class HookMatcher:
    matcher: str | None = None          # Pattern to match (None = match all)
    hooks: list[HookCallback] = field(default_factory=list)
    timeout: float | None = None        # Timeout in seconds
```

### AgentRunConfig addition

```python
@dataclass
class AgentRunConfig:
    # ... existing fields ...
    hooks: dict[HookEvent, list[HookMatcher]] | None = None
```

---

## New Module: `hooks.py`

A new module containing all hook-related logic.

### `build_hooks_config(hooks)`

Flattens the nested `{HookEvent: [HookMatcher]}` structure into two outputs:

**Input:**
```python
{
    "PreToolUse": [
        HookMatcher(matcher="Bash", hooks=[fn1, fn2]),
        HookMatcher(matcher=None, hooks=[fn3]),
    ]
}
```

**Output 1 — hooks_config (for CLI):**
```python
{
    "PreToolUse": [
        {"matcher": "Bash", "hookCallbackIds": ["hook_PreToolUse_0_0", "hook_PreToolUse_0_1"], "timeout": None},
        {"matcher": None, "hookCallbackIds": ["hook_PreToolUse_1_0"], "timeout": None},
    ]
}
```

**Output 2 — callback_registry:**
```python
{
    "hook_PreToolUse_0_0": fn1,
    "hook_PreToolUse_0_1": fn2,
    "hook_PreToolUse_1_0": fn3,
}
```

ID format: `f"hook_{event}_{matcher_idx}_{hook_idx}"` — deterministic and matches native SDK.

### `execute_hook(callback_id, hook_input, tool_use_id, callback_registry)`

Looks up and executes a hook callback:

1. Find callback by ID in registry
2. If not found: return `{"continue": True}` (pass-through)
3. Execute async callback: `await hook(hook_input, tool_use_id, {"signal": None})`
4. Map `continue_` → `continue` in output
5. On exception: return `{"continue": False, "stopReason": str(e)}`

### `build_control_response(request_id, response)`

Constructs a control response JSON message:

```python
{
    "type": "control_response",
    "response": {
        "subtype": "success",
        "request_id": request_id,
        "response": response
    }
}
```

### `build_initialize_request(hooks_config, request_id)`

Constructs an initialize control request:

```python
{
    "type": "control_request",
    "request_id": request_id,
    "request": {
        "subtype": "initialize",
        "hooks": hooks_config,
        "protocolVersion": "1.0"
    }
}
```

---

## SDK Integration: Changes to `sdk.py`

### Startup Phase (in `run_agent()`, after starting subprocess)

If `config.hooks` is not None and not empty:

1. Call `build_hooks_config(config.hooks)` → get `hooks_config` and `callback_registry`
2. Build initialize request via `build_initialize_request(hooks_config, request_id)`
3. Write the JSON to stdin
4. Read stdout lines until we get a `control_response` confirming initialization
5. Store `callback_registry` for the lifetime of the run

If `config.hooks` is None/empty: skip initialization entirely (backward compatible).

### Message Loop Changes

Current flow:
```
read line → parse_line() → yield event or handle internally
```

New flow:
```
read line → json.loads() →
  if type == "control_request":
    if subtype == "hook_callback":
      result = execute_hook(callback_id, input, tool_use_id, registry)
      write control_response to stdin
    # Don't yield control messages as events
  else:
    parse_line() → yield event (unchanged)
```

The key change is intercepting control messages **before** they reach `parse_line()`. This keeps the message parser clean and unchanged.

### Helper: `_write_to_stdin(process, data)`

```python
async def _write_to_stdin(process, data: dict) -> None:
    if process.stdin and not process.stdin.is_closing():
        process.stdin.write((json.dumps(data) + "\n").encode())
        await process.stdin.drain()
```

### What stays unchanged

- `MCPAgentSDK.__init__()`, `init()`, `shutdown()` — no changes
- MCP HTTP server (`mcp_server.py`) — no changes
- Complete/Block flow — no changes
- Timeout mechanism — no changes
- StderrReader — no changes
- Error handling — no changes
- All existing tests — should pass without modification

---

## Changes to `message_parser.py`

No changes needed. Control messages are intercepted before reaching the parser. The parser continues to handle only assistant/system/result message types.

---

## Changes to `process.py`

No changes needed. The stdin is already kept open (not closed after sending the prompt), which is exactly what we need for writing control responses back.

---

## Example: `hook_run()` in `example.py`

Add a new example function demonstrating PreToolUse hook to block dangerous Bash commands:

```python
async def hook_run():
    """Example 8: Use hooks to control agent behavior.

    Demonstrates PreToolUse hook that blocks dangerous shell commands
    like 'rm -rf' while allowing safe operations.
    """
    sdk = MCPAgentSDK()
    await sdk.init()

    async def block_dangerous_commands(hook_input, tool_use_id, context):
        """Block rm -rf and other dangerous Bash commands."""
        input_data = hook_input.get("input", {})
        command = input_data.get("command", "")
        if any(danger in command for danger in ["rm -rf", "mkfs", "dd if="]):
            return {
                "continue_": False,
                "decision": "block",
                "reason": f"Blocked dangerous command: {command}",
            }
        return {"continue_": True}

    try:
        config = AgentRunConfig(
            prompt="List files in the current directory and show disk usage",
            hooks={
                "PreToolUse": [
                    HookMatcher(
                        matcher="Bash",
                        hooks=[block_dangerous_commands],
                    )
                ]
            },
            permission_mode="bypassPermissions",
        )

        async for event in sdk.run_agent(config):
            if isinstance(event, AssistantMessage):
                for block in event.content:
                    if isinstance(block, TextBlock):
                        print(block.text)
            elif isinstance(event, AgentResult):
                print(f"\nResult: {event.status}")
                if event.message:
                    print(f"Message: {event.message}")
    finally:
        await sdk.shutdown()
```

Register in the main examples dictionary and add CLI dispatch.

---

## File Change Summary

| File | Change | Impact |
|------|--------|--------|
| `types.py` | Add HookEvent, HookContext, HookJSONOutput, HookCallback, HookMatcher; add `hooks` field to AgentRunConfig | New types only |
| `hooks.py` | **New file** — build_hooks_config, execute_hook, build_control_response, build_initialize_request | New module |
| `sdk.py` | Add initialization step and control_request handling in run_agent() message loop | Core change |
| `__init__.py` | Export new Hook types | API surface |
| `example.py` | Add hook_run() example | New example |

### Files NOT changed

- `mcp_server.py` — untouched
- `process.py` — untouched
- `message_parser.py` — untouched
- `errors.py` — untouched
- `prompt_template.py` — untouched
- All existing tests — should pass unmodified

---

## Testing Strategy

### Unit Tests (`test_hooks.py`)

1. `build_hooks_config` — correct ID generation, flattening, empty input handling
2. `execute_hook` — successful execution, missing callback, exception handling, continue_ mapping
3. `build_control_response` — correct JSON structure
4. `build_initialize_request` — correct JSON structure

### Integration Tests (additions to `test_sdk.py`)

1. `run_agent` with hooks — verify initialize request sent via stdin
2. Control request handling — verify hook_callback routed correctly
3. Control response — verify response written to stdin
4. No hooks — verify backward compatibility (no initialize sent)

---

## Edge Cases & Error Handling

- **Hook callback raises exception**: Return `{"continue": False, "stopReason": error_message}` — agent receives graceful stop signal
- **Unknown callback_id in control_request**: Return `{"continue": True}` — pass-through, don't block the agent
- **Hooks config is None or empty**: Skip initialize entirely — fully backward compatible
- **CLI doesn't support control protocol**: The initialize request will be ignored by older CLIs (they only read stream-json user messages). Hook callbacks won't be triggered. No crash, just no hook functionality.
- **Malformed control_request from CLI**: Log warning, skip, continue reading — don't crash the run
