## ADDED Requirements

### Requirement: can_use_tool callback support

MCPAgentSDK must support a `can_use_tool` async callback on `AgentRunConfig` that is invoked when the CLI subprocess sends a permission request for tool usage.

#### Scenario: No callback provided (default deny)

- **WHEN** `AgentRunConfig.can_use_tool` is `None` and CLI sends a `can_use_tool` control request
- **THEN** the SDK responds with `allowed: False` and reason `"Tool '<tool_name>' is not allowed: no permission handler provided"`

#### Scenario: Custom callback allows tool

- **WHEN** a custom `can_use_tool` callback returns `PermissionResultAllow()`
- **THEN** the SDK responds with `allowed: True` and forwards any `updated_input` to CLI

#### Scenario: Custom callback allows tool with modified input

- **WHEN** a custom `can_use_tool` callback returns `PermissionResultAllow(updated_input={...})`
- **THEN** the SDK responds with `allowed: True` and the `updatedInput` field contains the modified input

#### Scenario: Custom callback denies tool

- **WHEN** a custom `can_use_tool` callback returns `PermissionResultDeny(message="reason")`
- **THEN** the SDK responds with `allowed: False`, `reason: "reason"`, and `interrupt: False`

#### Scenario: Custom callback denies tool with interrupt

- **WHEN** a custom `can_use_tool` callback returns `PermissionResultDeny(message="reason", interrupt=True)`
- **THEN** the SDK responds with `allowed: False`, `reason: "reason"`, and `interrupt: True`

#### Scenario: Callback raises exception

- **WHEN** the `can_use_tool` callback raises an exception
- **THEN** the SDK responds with `allowed: False` and reason containing the exception message

### Requirement: Execution order with hooks

The `can_use_tool` callback operates on the CLI's permission request channel, separate from the hooks system. Hook `PreToolUse` callbacks are evaluated first by the CLI; if allowed, the CLI may then send a `can_use_tool` permission request which the SDK handles.

#### Scenario: Hook allows, can_use_tool denies

- **WHEN** a `PreToolUse` hook allows a tool call but `can_use_tool` returns deny
- **THEN** the tool call is denied

#### Scenario: Hook blocks before can_use_tool

- **WHEN** a `PreToolUse` hook blocks a tool call
- **THEN** no `can_use_tool` request is sent; the tool is blocked at the hook level

### Requirement: Type definitions aligned with codebuddy_agent_sdk

New types must be provided and publicly exported:

- `CanUseToolOptions(tool_use_id: str, agent_id: str | None)`
- `PermissionResultAllow(behavior: "allow", updated_input: dict | None)`
- `PermissionResultDeny(behavior: "deny", message: str, interrupt: bool)`
- `PermissionResult = PermissionResultAllow | PermissionResultDeny`
- `CanUseTool = Callable[[str, dict, CanUseToolOptions], Awaitable[PermissionResult]]`
- `default_deny_can_use_tool` async function
