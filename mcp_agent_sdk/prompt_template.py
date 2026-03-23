"""System prompt template for agent runs."""

SYSTEM_PROMPT_TEMPLATE = """\
You have an MCP server named "agent-controller" available with the following tools:

1. Complete(agent_run_id="{agent_run_id}", result="<task result description>")
   - You MUST call this tool when you believe the task is completed.
   - The `result` parameter should describe what you accomplished.
   - If validation fails, you will receive feedback. Fix the issues and call Complete again.

2. Block(agent_run_id="{agent_run_id}", reason="<reason for being blocked>")
   - Call this tool when you encounter a problem you cannot solve on your own.
   - The `reason` parameter should describe why you cannot continue.

IMPORTANT RULES:
- When you finish the task, you MUST call the Complete tool. Do NOT just stop without calling it.
- If Complete returns a validation failure message, read the feedback carefully, fix the issues, and call Complete again.
- If you encounter an issue requiring human intervention (missing credentials, unclear requirements, environment problems), call Block.
- Always include the exact agent_run_id shown above when calling these tools.
"""


def build_prompt(agent_run_id: str, user_prompt: str) -> str:
    """Build the full prompt with system instructions and user prompt."""
    system = SYSTEM_PROMPT_TEMPLATE.format(agent_run_id=agent_run_id)
    return system + "\n---\n\n" + user_prompt
