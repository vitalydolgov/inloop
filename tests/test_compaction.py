"""Tests for context compaction."""

import asyncio
from collections.abc import AsyncIterator, Sequence

from inloop.app import compaction
from inloop.domain import message
from inloop.domain.message import Message, Role
from inloop.domain import streaming
from inloop.domain import tool


class _SummaryModel:
    """A Model that answers any request with a fixed summary, recording what it saw."""

    def __init__(self, summary: str) -> None:
        self._summary = summary
        self.seen: list[list[message.Message]] = []

    @property
    def context_window(self) -> int:
        return 1000

    async def stream(
        self,
        messages: Sequence[message.Message],
        tools: Sequence[tool.Tool] = (),
        system: str = "",
    ) -> AsyncIterator[streaming.Event]:
        self.seen.append(list(messages))
        yield streaming.MessageCompleted(text=self._summary, stop_reason="end_turn", input_tokens=0)


def test_is_full_compares_against_the_threshold() -> None:
    compactor = compaction.Compactor(_SummaryModel("s"), threshold=0.8)

    assert not compactor.is_full(799)
    assert compactor.is_full(800)
    assert compactor.is_full(1200)


def test_compact_summarizes_older_turns_and_keeps_the_latest() -> None:
    model = _SummaryModel("BRIEFING")
    compactor = compaction.Compactor(model)
    history = [
        Message(Role.USER, [message.Text("first")]),
        Message(Role.ASSISTANT, [message.Text("reply one")]),
        Message(Role.USER, [message.Text("second")]),
    ]

    result = asyncio.run(compactor.compact(history))

    assert len(result) == 1
    text = result[0].content[0].text
    assert compaction.SUMMARY_HEADING in text
    assert "BRIEFING" in text
    assert text.endswith("second")
    assert model.seen[0] == [
        Message(Role.USER, [message.Text("first")]),
        Message(Role.ASSISTANT, [message.Text("reply one")]),
        Message(Role.USER, [message.Text(compaction.SUMMARY_INSTRUCTION)]),
    ]


def test_compact_keeps_the_current_turns_tool_exchange_verbatim() -> None:
    model = _SummaryModel("BRIEFING")
    compactor = compaction.Compactor(model)
    call = message.ToolCall("c1", "test__work", {})
    result_block = message.ToolResult("c1", "done")
    history = [
        Message(Role.USER, [message.Text("old")]),
        Message(Role.ASSISTANT, [message.Text("earlier")]),
        Message(Role.USER, [message.Text("current")]),
        Message(Role.ASSISTANT, [call]),
        Message(Role.USER, [result_block]),
    ]

    result = asyncio.run(compactor.compact(history))

    assert result[1:] == [
        Message(Role.ASSISTANT, [call]),
        Message(Role.USER, [result_block]),
    ]
    assert result[0].content[0].text.endswith("current")


def test_compact_leaves_a_single_turn_untouched() -> None:
    model = _SummaryModel("BRIEFING")
    compactor = compaction.Compactor(model)
    history = [Message(Role.USER, [message.Text("only")])]

    result = asyncio.run(compactor.compact(history))

    assert result == history
    assert model.seen == []
