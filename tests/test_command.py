"""Tests for commands the user addresses to the harness rather than the model."""

import asyncio

from inloop.app import agent
from inloop.app.command import Command
from inloop.app.server_tools import ServerTools
from inloop.domain import streaming
from inloop.domain.tool import ToolSpec

from tests.test_agent import _ScriptedModel, _stream
from tests.test_mcp import _FakeServer, _FakeSource


def _run(chat_agent, messages):
    async def gather():
        return [event async for event in chat_agent.events(_stream(messages))]

    return asyncio.run(gather())


def test_reload_swaps_the_tools_offered_to_the_model() -> None:
    source = _FakeSource({"calculator": _FakeServer([ToolSpec("add", "Add.", {})])})
    model = _ScriptedModel(["done"])

    async def run():
        async with ServerTools(source) as hosted:
            chat_agent = agent.Agent(
                model,
                server_tools=hosted,
                commands=[Command("reload", "reconnect the tool servers", hosted.reload)],
                _spawn=False,
            )
            source.servers = {"painter": _FakeServer([ToolSpec("draw", "Draw.", {})])}
            return [e async for e in chat_agent.events(_stream(["/reload", "draw a cat"]))]

    events = asyncio.run(run())

    assert streaming.CommandCompleted("reload") in events
    assert [t.name for t in model.offered_tools[0]] == ["painter__draw"]


def test_a_command_leaves_the_conversation_untouched() -> None:
    model = _ScriptedModel([])
    source = _FakeSource({"calculator": _FakeServer([ToolSpec("add", "Add.", {})])})

    async def run():
        async with ServerTools(source) as hosted:
            chat_agent = agent.Agent(
                model,
                server_tools=hosted,
                commands=[Command("reload", "reconnect the tool servers", hosted.reload)],
            )
            async for _ in chat_agent.events(_stream(["/reload"])):
                pass
            return chat_agent

    chat_agent = asyncio.run(run())

    assert chat_agent.conversation.history == []
    assert model.seen == []


def test_unknown_command_is_reported_as_a_failure() -> None:
    async def reload():
        pass

    chat_agent = agent.Agent(
        _ScriptedModel([]),
        commands=[Command("reload", "reconnect the tool servers", reload)],
    )

    events = _run(chat_agent, ["/refresh"])

    assert events == [streaming.Failed("unknown command: /refresh")]
    assert chat_agent.conversation.history == []


def test_a_failing_command_is_reported_as_a_failure() -> None:
    async def reload():
        raise RuntimeError("no such command")

    chat_agent = agent.Agent(
        _ScriptedModel([]),
        commands=[Command("reload", "reconnect the tool servers", reload)],
    )

    events = _run(chat_agent, ["/reload"])

    assert events == [streaming.Failed("/reload failed: no such command")]


def test_a_message_is_not_taken_for_a_command_when_none_are_available() -> None:
    model = _ScriptedModel(["I cannot"])

    chat_agent = agent.Agent(model)
    _run(chat_agent, ["/reload the page"])

    assert len(model.seen) == 1
