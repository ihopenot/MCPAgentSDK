## Context

MCPAgentSDK manages CLI subprocesses that communicate via stdout/stdin control protocol. The SDK already handles `hook_callback` control requests. The CLI can also send `can_use_tool` permission requests when `permission_mode` is not `"bypassPermissions"`, but the SDK currently has no handler for these, causing the agent to hang.

Reference implementation: `codebuddy_agent_sdk` (Python package) provides a `can_use_tool` callback with `CanUseToolOptions`, `PermissionResultAllow`, `PermissionResultDeny` types.

## Goals / Non-Goals

**Goals:**
- Add `can_use_tool` callback to `AgentRunConfig` for programmatic tool permission control
- Provide `default_deny_can_use_tool` that rejects all tools when no handler is set
- Handle `can_use_tool` control requests in SDK's event loop alongside existing hook handling
- Align type definitions with `codebuddy_agent_sdk` for API consistency

**Non-Goals:**
- Not implementing `signal`, `suggestions`, `blocked_path`, `decision_reason` fields from `codebuddy_agent_sdk`'s `CanUseToolOptions` (not applicable to MCPAgentSDK's architecture)
- Not implementing `updated_permissions` from `PermissionResultAllow` (MCPAgentSDK has no permission rules system)
- Not changing the hooks system or existing `allowed_tools` mechanism

## Decisions

1. **Type alignment with codebuddy_agent_sdk**: Use same dataclass pattern (`PermissionResultAllow`/`PermissionResultDeny` with `behavior` literal field) but omit fields irrelevant to MCPAgentSDK
2. **Default behavior**: `can_use_tool=None` triggers `default_deny_can_use_tool` internally, preventing agent hangs
3. **Integration point**: Handle `can_use_tool` as a new `subtype` branch in the existing control request processing (sdk.py), same pattern as `hook_callback`
4. **Exception handling**: Callback exceptions are caught and converted to deny responses, preventing SDK crashes
5. **No hook interference**: `can_use_tool` and hooks are independent channels; both can coexist

## Risks / Trade-offs

- **Minimal risk**: Changes are additive; existing behavior is unchanged when `permission_mode="bypassPermissions"`
- **Default deny may surprise users**: Users switching from `bypassPermissions` to another mode will see all tools denied unless they provide a `can_use_tool` handler. This is intentional and safe (fail-closed)
