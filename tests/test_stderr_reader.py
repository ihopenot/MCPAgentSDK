"""Tests for stderr async reader and buffer."""

import asyncio

import pytest

from mcp_agent_sdk.process import StderrReader


@pytest.fixture
def make_mock_stderr():
    """Create a mock stderr stream from given lines."""

    def _factory(lines: list[str]):
        data = "".join(line + "\n" for line in lines).encode()

        class MockStream:
            def __init__(self):
                self._buffer = asyncio.StreamReader()
                self._buffer.feed_data(data)
                self._buffer.feed_eof()

            async def readline(self):
                return await self._buffer.readline()

        return MockStream()

    return _factory


class TestStderrReader:
    """StderrReader captures stderr lines into a bounded deque."""

    @pytest.mark.asyncio
    async def test_captures_lines(self, make_mock_stderr):
        stderr = make_mock_stderr(["line1", "line2", "line3"])
        reader = StderrReader(stderr, maxlen=100)
        task = reader.start()
        await task  # wait for EOF
        assert reader.get_output() == "line1\nline2\nline3"

    @pytest.mark.asyncio
    async def test_bounded_buffer(self, make_mock_stderr):
        lines = [f"line{i}" for i in range(200)]
        stderr = make_mock_stderr(lines)
        reader = StderrReader(stderr, maxlen=5)
        task = reader.start()
        await task
        output = reader.get_output()
        # Should only keep last 5 lines
        assert output == "line195\nline196\nline197\nline198\nline199"

    @pytest.mark.asyncio
    async def test_empty_stderr(self, make_mock_stderr):
        stderr = make_mock_stderr([])
        reader = StderrReader(stderr, maxlen=100)
        task = reader.start()
        await task
        assert reader.get_output() == ""

    @pytest.mark.asyncio
    async def test_get_lines(self, make_mock_stderr):
        stderr = make_mock_stderr(["a", "b", "c"])
        reader = StderrReader(stderr, maxlen=100)
        task = reader.start()
        await task
        assert reader.get_lines() == ["a", "b", "c"]
