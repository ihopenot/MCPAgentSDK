"""Hook support: config building, callback execution, control protocol messages."""

from __future__ import annotations

from typing import Any

from mcp_agent_sdk.types import HookCallback, HookMatcher


def build_hooks_config(
    hooks: dict[Any, list[HookMatcher]] | None,
) -> tuple[dict[str, list[dict[str, Any]]] | None, dict[str, HookCallback]]:
    """Build hooks configuration for CLI and callback registry.

    Flattens the nested {HookEvent: [HookMatcher]} structure into:
    - config: JSON-serializable dict to send to CLI in the initialize request
    - callbacks: {callback_id: hook_function} mapping for runtime lookup

    Returns:
        Tuple of (config_for_cli, callback_registry).
        config_for_cli is None if hooks is None or empty.
    """
    callbacks: dict[str, HookCallback] = {}

    if not hooks:
        return None, callbacks

    config: dict[str, list[dict[str, Any]]] = {}

    for event, matchers in hooks.items():
        event_str = str(event)
        matcher_configs = []

        for i, m in enumerate(matchers):
            callback_ids = []
            for j, hook in enumerate(m.hooks):
                callback_id = f"hook_{event_str}_{i}_{j}"
                callback_ids.append(callback_id)
                callbacks[callback_id] = hook

            matcher_configs.append(
                {
                    "matcher": m.matcher,
                    "hookCallbackIds": callback_ids,
                    "timeout": m.timeout,
                }
            )

        config[event_str] = matcher_configs

    return (config if config else None), callbacks


async def execute_hook(
    callback_id: str,
    hook_input: dict[str, Any],
    tool_use_id: str | None,
    hook_callbacks: dict[str, HookCallback],
) -> dict[str, Any]:
    """Execute a hook callback by looking up in the callback registry.

    Args:
        callback_id: The deterministic ID of the hook callback.
        hook_input: Input data from the CLI (tool name, args, etc.).
        tool_use_id: The tool use ID if applicable, None otherwise.
        hook_callbacks: The callback registry from build_hooks_config.

    Returns:
        Dict with hook response. Always includes "continue" key.
        On missing callback: {"continue": True} (pass-through).
        On exception: {"continue": False, "stopReason": error_message}.
    """
    hook = hook_callbacks.get(callback_id)
    if not hook:
        return {"continue": True}

    try:
        result = await hook(hook_input, tool_use_id, {"signal": None})
        output = dict(result)
        # Map Python-safe key 'continue_' back to 'continue' for CLI protocol
        if "continue_" in output:
            output["continue"] = output.pop("continue_")
        return output
    except Exception as e:
        return {"continue": False, "stopReason": str(e)}


def build_control_response(request_id: str, response: dict[str, Any]) -> dict[str, Any]:
    """Build a success control response envelope.

    Args:
        request_id: The request ID from the incoming control request.
        response: The response payload (hook result, etc.).

    Returns:
        Complete control_response JSON-serializable dict.
    """
    return {
        "type": "control_response",
        "response": {
            "subtype": "success",
            "request_id": request_id,
            "response": response,
        },
    }


def build_initialize_request(
    hooks_config: dict[str, list[dict[str, Any]]] | None,
    request_id: str,
) -> dict[str, Any]:
    """Build an initialize control request with hooks configuration.

    Args:
        hooks_config: The CLI-facing hooks config from build_hooks_config.
        request_id: Unique ID for this request.

    Returns:
        Complete control_request JSON-serializable dict.
    """
    return {
        "type": "control_request",
        "request_id": request_id,
        "request": {
            "subtype": "initialize",
            "hooks": hooks_config,
            "protocolVersion": "1.0",
        },
    }
