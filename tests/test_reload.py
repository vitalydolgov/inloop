"""Tests for the built-in agent__reload tool."""

import asyncio
from collections.abc import AsyncIterator

from inloop.app import agent
from inloop.app import reload
from inloop.app.server_tools import ServerTools
from inloop.domain import message
from inloop.domain import streaming
from inloop.domain import tool
from inloop.domain.tool import ToolSpec

from tests.test_agent import _ScriptedModel, _stream
from tests.test_mcp import _BrokenServer, _FakeServer, _FakeSource


class _RecordingTurnModel:
    """A Model that yields a scripted list of events per turn and records offered tools."""

    context_window = 0

    def __init__(self, turns: list[list[streaming.Event]]) -> None:
        self._turns = iter(turns)
        self.seen: list[list[message.Message]] = []
        self.offered_tools: list[list[tool.Tool]] = []

    async def stream(
        self,
        messages: list[message.Message],
        tools: list[tool.Tool] = [],
        system: str = "",
    ) -> AsyncIterator[streaming.Event]:
        self.seen.append(list(messages))
        self.offered_tools.append(list(tools))
        for event in next(self._turns):
            yield event


def test_reload_tool_is_offered_when_server_tools_are_configured() -> None:
    source = _FakeSource({"calculator": _FakeServer([ToolSpec("add", "Add.", {})])})
    model = _ScriptedModel(["done"])

    async def run():
        async with ServerTools(source) as hosted:
            chat_agent = agent.Agent(model, server_tools=hosted, _spawn=False)
            async for _ in chat_agent.events(_stream(["hello"])):
                pass

    asyncio.run(run())

    names = [t.name for t in model.offered_tools[0]]
    assert reload.TOOL_NAME in names
    assert "calculator__add" in names


def test_reload_tool_is_absent_without_server_tools() -> None:
    model = _ScriptedModel(["done"])
    chat_agent = agent.Agent(model, _spawn=False)

    async def run():
        async for _ in chat_agent.events(_stream(["hello"])):
            pass

    asyncio.run(run())

    assert [t.name for t in model.offered_tools[0]] == []


def test_reload_swaps_the_tools_offered_on_the_next_turn() -> None:
    source = _FakeSource({"calculator": _FakeServer([ToolSpec("add", "Add.", {})])})
    model = _RecordingTurnModel(
        [
            [
                streaming.ToolUse(id="c1", name=reload.TOOL_NAME, input={}),
                streaming.MessageCompleted(text="", stop_reason="tool_use", input_tokens=0),
            ],
            [
                streaming.TextDelta("done"),
                streaming.MessageCompleted(text="done", stop_reason="end_turn", input_tokens=0),
            ],
        ]
    )

    async def run():
        async with ServerTools(source) as hosted:
            chat_agent = agent.Agent(model, server_tools=hosted, _spawn=False)
            source.servers = {"painter": _FakeServer([ToolSpec("draw", "Draw.", {})])}
            events = [e async for e in chat_agent.events(_stream(["reload servers"]))]
            return events, chat_agent

    events, chat_agent = asyncio.run(run())

    assert not any(isinstance(e, streaming.Failed) for e in events)
    assert [t.name for t in model.offered_tools[0]] == ["calculator__add", reload.TOOL_NAME]
    assert [t.name for t in model.offered_tools[1]] == ["painter__draw", reload.TOOL_NAME]

    results = [
        b
        for m in chat_agent.conversation.history
        for b in m.content
        if isinstance(b, message.ToolSuccess)
    ]
    assert len(results) == 1
    assert results[0].content == "reconnected: painter"


def test_reload_failure_is_returned_as_a_tool_error() -> None:
    live = _FakeServer([ToolSpec("a", "A.", {})])
    source = _FakeSource({"one": live})
    model = _RecordingTurnModel(
        [
            [
                streaming.ToolUse(id="c1", name=reload.TOOL_NAME, input={}),
                streaming.MessageCompleted(text="", stop_reason="tool_use", input_tokens=0),
            ],
            [
                streaming.MessageCompleted(
                    text="could not reload", stop_reason="end_turn", input_tokens=0
                ),
            ],
        ]
    )

    async def run():
        async with ServerTools(source) as hosted:
            chat_agent = agent.Agent(model, server_tools=hosted, _spawn=False)
            source.servers = {"two": _BrokenServer()}
            events = [e async for e in chat_agent.events(_stream(["reload"]))]
            return events, chat_agent, [t.name for t in hosted.tools()], live.closed

    events, chat_agent, tools, closed = asyncio.run(run())

    assert not any(isinstance(e, streaming.Failed) for e in events)
    assert tools == ["one__a"]
    assert not closed

    failures = [
        b
        for m in chat_agent.conversation.history
        for b in m.content
        if isinstance(b, message.ToolFailure)
    ]
    assert len(failures) == 1
    assert "error: no such command" in failures[0].content
