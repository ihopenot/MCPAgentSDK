## Why

MCPAgentSDK currently lacks a permission callback mechanism for tool usage. When the CLI subprocess sends permission requests (e.g., in non-bypass permission modes), the SDK has no handler, causing the agent to hang waiting for approval. Users need a programmatic way to approve or deny tool calls at runtime, similar to `codebuddy_agent_sdk`'s `can_use_tool` callback.

## What Changes

- Add `can_use_tool` callback parameter to `AgentRunConfig` for runtime tool permission decisions
- Add type definitions aligned with `codebuddy_agent_sdk`: `CanUseToolOptions`, `PermissionResultAllow`, `PermissionResultDeny`, `PermissionResult`, `CanUseTool`
- Add `default_deny_can_use_tool` function that rejects all tool calls when no custom handler is provided
- Handle `can_use_tool` control requests from CLI subprocess in the SDK's event loop
- Export all new public types from `__init__.py`

## Impact

- **types.py**: New dataclasses and type aliases added; `AgentRunConfig` gains `can_use_tool` field
- **sdk.py**: New control request branch for `can_use_tool` subtype in the stdout processing loop
- **__init__.py**: Additional exports for new public types
- **No breaking changes**: `can_use_tool` defaults to `None`, which triggers `default_deny_can_use_tool` internally. Existing code using `permission_mode="bypassPermissions"` is unaffected since CLI won't send permission requests in that mode.
