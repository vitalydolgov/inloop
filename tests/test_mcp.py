"""Tests for adapting a tool server's tools into agent tools."""

import asyncio

import pytest

from inloop.app import agent
from inloop.app import tool_server
from inloop.app.server_tools import ServerTools
from inloop.domain import message
from inloop.domain import streaming
from inloop.domain.tool import ToolSpec

from tests.test_agent import _TurnModel, _stream


class _FakeServer:
    """A ToolServer that advertises fixed specs and records the calls it receives."""

    def __init__(self, specs: list[ToolSpec], results: dict[str, str] | None = None) -> None:
        self._specs = specs
        self._results = results or {}
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.connected = False
        self.closed = False

    async def connect(self) -> None:
        self.connected = True

    async def aclose(self) -> None:
        self.closed = True

    async def list_tools(self) -> list[ToolSpec]:
        return self._specs

    async def call_tool(self, name: str, arguments: dict[str, object]) -> str:
        self.calls.append((name, arguments))
        result = self._results.get(name, "ok")
        if isinstance(result, Exception):
            raise result
        return result


class _BrokenServer:
    """A ToolServer that fails to connect."""

    def __init__(self) -> None:
        self.closed = False

    async def connect(self) -> None:
        raise RuntimeError("no such command")

    async def aclose(self) -> None:
        self.closed = True


class _FakeSource:
    """A ToolServerConfig whose servers can change between loads."""

    def __init__(self, servers: dict[str, object]) -> None:
        self.servers = servers

    def load(self) -> dict[str, object]:
        return dict(self.servers)


def test_loads_advertised_specs_as_namespaced_tools() -> None:
    specs = [
        ToolSpec("add", "Add two numbers.", {"type": "object", "properties": {"a": {}, "b": {}}}),
        ToolSpec("subtract", "Subtract one number from another.", {"type": "object", "properties": {}}),
    ]
    server = _FakeServer(specs)

    tools = asyncio.run(tool_server.make_tools("calculator", server))

    assert [t.name for t in tools] == ["calculator__add", "calculator__subtract"]
    add = tools[0]
    assert add.description == "Add two numbers."
    assert add.parameters == {"type": "object", "properties": {"a": {}, "b": {}}}


def test_tool_proxies_call_to_the_server() -> None:
    server = _FakeServer([ToolSpec("shout", "Uppercase.", {})], {"shout": "HELLO"})

    tools = asyncio.run(tool_server.make_tools("echo", server))
    result = asyncio.run(tools[0].execute({"text": "hello"}))

    assert result == "HELLO"
    assert server.calls == [("shout", {"text": "hello"})]


def test_each_tool_proxies_under_its_own_name() -> None:
    specs = [ToolSpec("first", "First.", {}), ToolSpec("second", "Second.", {})]
    server = _FakeServer(specs)

    tools = {t.name: t for t in asyncio.run(tool_server.make_tools("srv", server))}
    asyncio.run(tools["srv__second"].execute({"x": 1}))

    assert server.calls == [("second", {"x": 1})]


def test_opens_every_configured_server_and_exposes_its_tools() -> None:
    first = _FakeServer([ToolSpec("a", "A.", {})])
    second = _FakeServer([ToolSpec("b", "B.", {})])

    async def run():
        source = _FakeSource({"one": first, "two": second})
        async with ServerTools(source) as hosted:
            assert first.connected and second.connected
            return [t.name for t in hosted.tools()]

    assert asyncio.run(run()) == ["one__a", "two__b"]
    assert first.closed and second.closed


def test_skips_broken_servers_and_keeps_the_working_ones() -> None:
    good = _FakeServer([ToolSpec("a", "A.", {})])
    broken = _BrokenServer()

    async def run():
        source = _FakeSource({"good": good, "broken": broken})
        async with ServerTools(source) as hosted:
            return [t.name for t in hosted.tools()], hosted.errors()

    names, errors = asyncio.run(run())

    assert names == ["good__a"]
    assert "broken" in errors
    assert "no such command" in str(errors["broken"])


def test_closes_servers_when_the_body_raises() -> None:
    server = _FakeServer([ToolSpec("a", "A.", {})])

    async def run():
        async with ServerTools(_FakeSource({"one": server})):
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        asyncio.run(run())

    assert server.closed


def test_reload_connects_the_newly_configured_servers_and_drops_the_old_ones() -> None:
    old = _FakeServer([ToolSpec("a", "A.", {})])
    new = _FakeServer([ToolSpec("b", "B.", {}), ToolSpec("c", "C.", {})])

    async def run():
        source = _FakeSource({"one": old})
        async with ServerTools(source) as hosted:
            source.servers = {"two": new}
            await hosted.reload()
            return [t.name for t in hosted.tools()], hosted.servers()

    names, servers = asyncio.run(run())

    assert names == ["two__b", "two__c"]
    assert servers == ["two"]
    assert old.closed and new.connected


def test_reload_keeps_the_live_servers_when_the_new_ones_fail_to_connect() -> None:
    live = _FakeServer([ToolSpec("a", "A.", {})])
    broken = _BrokenServer()

    async def run():
        source = _FakeSource({"one": live})
        async with ServerTools(source) as hosted:
            source.servers = {"two": broken}
            with pytest.raises(RuntimeError):
                await hosted.reload()
            return [t.name for t in hosted.tools()], live.closed

    names, closed = asyncio.run(run())

    assert names == ["one__a"]
    assert not closed


def test_mcp_error_result_is_returned_to_model() -> None:
    specs = [ToolSpec("flaky", "A tool that can fail.", {})]
    server = _FakeServer(specs, {"flaky": RuntimeError("try again in a second")})

    model = _TurnModel(
        [
            [
                streaming.ToolUse(id="c1", name="testretry__flaky", input={}),
                streaming.MessageCompleted(text="", stop_reason="tool_use", input_tokens=0),
            ],
            [
                streaming.MessageCompleted(text="I will retry later.", stop_reason="end_turn", input_tokens=0),
            ],
        ]
    )

    async def run():
        source = _FakeSource({"testretry": server})
        async with ServerTools(source) as hosted:
            chat_agent = agent.Agent(model, server_tools=hosted)
            events = [event async for event in chat_agent.events(_stream(["use the flaky tool"]))]
            return events, chat_agent

    events, chat_agent = asyncio.run(run())

    assert not any(isinstance(e, streaming.Failed) for e in events)

    failures = [
        b for m in chat_agent.conversation.history
        for b in m.content
        if isinstance(b, message.ToolFailure)
    ]
    assert len(failures) == 1
    assert "error: try again in a second" in failures[0].content
