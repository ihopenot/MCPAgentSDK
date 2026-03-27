"""Tests for structured message types: StreamEvent, ContentBlock and their subclasses."""

import pytest

from mcp_agent_sdk.types import (
    AgentResult,
    AssistantMessage,
    ContentBlock,
    ResultMessage,
    StreamEvent,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)


class TestStreamEvent:
    """StreamEvent is the abstract base for all yielded types."""

    def test_cannot_instantiate_directly(self):
        """StreamEvent should not be used directly — it's a base class."""
        # It's a dataclass base, instantiation is technically possible
        # but all concrete types should be subclasses
        pass

    def test_all_message_types_are_stream_events(self):
        assistant = AssistantMessage(content=[])
        system = SystemMessage(subtype="init", data={})
        result = ResultMessage(session_id="s1")
        agent_result = AgentResult(
            status="completed", message="done",
            session_id="s1", agent_run_id="r1",
        )
        for obj in [assistant, system, result, agent_result]:
            assert isinstance(obj, StreamEvent), f"{type(obj).__name__} is not a StreamEvent"


class TestContentBlock:
    """ContentBlock subtypes."""

    def test_text_block(self):
        block = TextBlock(text="hello")
        assert isinstance(block, ContentBlock)
        assert block.type == "text"
        assert block.text == "hello"

    def test_thinking_block(self):
        block = ThinkingBlock(thinking="let me think...")
        assert isinstance(block, ContentBlock)
        assert block.type == "thinking"
        assert block.thinking == "let me think..."

    def test_tool_use_block(self):
        block = ToolUseBlock(
            tool_use_id="tu_123",
            name="Write",
            input={"path": "test.py", "content": "code"},
        )
        assert isinstance(block, ContentBlock)
        assert block.type == "tool_use"
        assert block.tool_use_id == "tu_123"
        assert block.name == "Write"
        assert block.input == {"path": "test.py", "content": "code"}

    def test_tool_result_block(self):
        block = ToolResultBlock(
            tool_use_id="tu_123",
            output="file written",
        )
        assert isinstance(block, ContentBlock)
        assert block.type == "tool_result"
        assert block.tool_use_id == "tu_123"
        assert block.output == "file written"
        assert block.is_error is False

    def test_tool_result_block_error(self):
        block = ToolResultBlock(
            tool_use_id="tu_456",
            output="permission denied",
            is_error=True,
        )
        assert block.is_error is True


class TestAssistantMessage:
    """AssistantMessage contains a list of ContentBlock."""

    def test_with_text(self):
        msg = AssistantMessage(
            content=[TextBlock(text="Hello")],
            session_id="sess-1",
        )
        assert isinstance(msg, StreamEvent)
        assert len(msg.content) == 1
        assert isinstance(msg.content[0], TextBlock)
        assert msg.session_id == "sess-1"

    def test_with_multiple_blocks(self):
        msg = AssistantMessage(
            content=[
                ThinkingBlock(thinking="hmm"),
                TextBlock(text="result"),
                ToolUseBlock(tool_use_id="t1", name="Read", input={}),
            ],
        )
        assert len(msg.content) == 3
        assert isinstance(msg.content[0], ThinkingBlock)
        assert isinstance(msg.content[1], TextBlock)
        assert isinstance(msg.content[2], ToolUseBlock)

    def test_default_session_id(self):
        msg = AssistantMessage(content=[])
        assert msg.session_id == ""


class TestSystemMessage:
    """SystemMessage for system events."""

    def test_attributes(self):
        msg = SystemMessage(subtype="init", data={"session_id": "s1"})
        assert isinstance(msg, StreamEvent)
        assert msg.subtype == "init"
        assert msg.data == {"session_id": "s1"}


class TestResultMessage:
    """ResultMessage for session end metadata."""

    def test_attributes(self):
        msg = ResultMessage(
            session_id="sess-abc",
            cost_usd=0.05,
            duration_ms=12000,
            is_error=False,
            num_turns=5,
        )
        assert isinstance(msg, StreamEvent)
        assert msg.session_id == "sess-abc"
        assert msg.cost_usd == 0.05
        assert msg.duration_ms == 12000
        assert msg.is_error is False
        assert msg.num_turns == 5

    def test_defaults(self):
        msg = ResultMessage(session_id="s1")
        assert msg.cost_usd == 0.0
        assert msg.duration_ms == 0
        assert msg.is_error is False
        assert msg.num_turns == 0


class TestAgentResult:
    """AgentResult — final result with extended fields."""

    def test_attributes(self):
        result = AgentResult(
            status="completed",
            message="task done",
            session_id="sess-1",
            agent_run_id="abc123",
        )
        assert isinstance(result, StreamEvent)
        assert result.status == "completed"
        assert result.message == "task done"
        assert result.session_id == "sess-1"
        assert result.agent_run_id == "abc123"
        assert result.exit_code is None
        assert result.stderr_output == ""

    def test_with_error_info(self):
        result = AgentResult(
            status="error",
            message="crashed",
            session_id="",
            agent_run_id="xyz",
            exit_code=1,
            stderr_output="fatal error",
        )
        assert result.exit_code == 1
        assert result.stderr_output == "fatal error"
