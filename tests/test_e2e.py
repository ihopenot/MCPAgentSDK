"""End-to-end tests using real codebuddy CLI."""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
import uuid

import pytest

from mcp_agent_sdk import MCPAgentSDK
from mcp_agent_sdk.types import AgentRunConfig

# Skip all tests in this module if codebuddy is not available
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        shutil.which("codebuddy") is None,
        reason="codebuddy CLI not found in PATH",
    ),
]


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        yield tmpdir


@pytest.fixture
async def sdk():
    """Create and initialize SDK, cleanup after test."""
    inst = MCPAgentSDK()
    await inst.init()
    yield inst
    await inst.shutdown()


@pytest.mark.asyncio
@pytest.mark.timeout(120)
async def test_complete_with_file_validation(sdk, temp_dir):
    """Agent creates a random file, validate_fn verifies it exists,
    on_complete callback records success."""
    random_filename = f"test_file_{uuid.uuid4().hex[:8]}.txt"
    expected_path = os.path.join(temp_dir, random_filename)

    on_complete_called = asyncio.Event()
    complete_results: list[str] = []

    def validate_fn(result: str) -> tuple[bool, str]:
        if os.path.exists(expected_path):
            return (True, "")
        return (False, f"File {expected_path} does not exist")

    def on_complete(result: str):
        complete_results.append(result)
        on_complete_called.set()

    prompt = (
        f'Create a file named exactly "{random_filename}" in the current working directory. '
        f'The file should contain the text "Hello from E2E test". '
        f"After creating the file, call the Complete tool to finish."
    )

    config = AgentRunConfig(
        prompt=prompt,
        validate_fn=validate_fn,
        on_complete=on_complete,
        cwd=temp_dir,
        max_retries=3,
    )

    messages = []
    final_result = None

    async for msg in sdk.run_agent(config):
        messages.append(msg)
        if msg.type == "agent_result":
            final_result = msg

    assert final_result is not None, "Should have received agent_result message"
    assert final_result.content["status"] == "completed", (
        f"Expected completed, got {final_result.content}"
    )
    assert on_complete_called.is_set(), "on_complete callback should have been called"
    assert len(complete_results) == 1, "on_complete should have been called exactly once"
    assert os.path.exists(expected_path), f"File {expected_path} should exist"


@pytest.mark.asyncio
@pytest.mark.timeout(120)
async def test_block_with_reason(sdk, temp_dir):
    """Agent immediately calls Block tool, on_block callback records the reason."""
    on_block_called = asyncio.Event()
    block_reasons: list[str] = []
    expected_reason = "User requested immediate block for testing"

    def on_block(reason: str):
        block_reasons.append(reason)
        on_block_called.set()

    prompt = (
        f"IMPORTANT: Do NOT attempt to complete any task. "
        f'You must IMMEDIATELY call the Block tool with this exact reason: "{expected_reason}" '
        f"Do not do anything else. Just call Block with that reason."
    )

    config = AgentRunConfig(
        prompt=prompt,
        validate_fn=None,
        on_complete=None,
        on_block=on_block,
        cwd=temp_dir,
        max_retries=3,
    )

    messages = []
    final_result = None

    async for msg in sdk.run_agent(config):
        messages.append(msg)
        if msg.type == "agent_result":
            final_result = msg

    assert final_result is not None, "Should have received agent_result message"
    assert final_result.content["status"] == "blocked", (
        f"Expected blocked, got {final_result.content}"
    )
    assert on_block_called.is_set(), "on_block callback should have been called"
    assert len(block_reasons) == 1, "on_block should have been called exactly once"
    assert expected_reason in block_reasons[0], (
        f"Block reason should contain expected text, got: {block_reasons[0]}"
    )
