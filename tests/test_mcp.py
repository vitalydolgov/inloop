"""Tests for adapting a tool server's tools into an agent extension."""

import asyncio

from inloop.app import tool_server
from inloop.domain.tool import ToolSpec


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
        return self._results.get(name, "ok")


class _FakeSource:
    """A ToolServerSource that hands back a fixed set of servers."""

    def __init__(self, servers: dict[str, _FakeServer]) -> None:
        self._servers = servers

    def load(self) -> dict[str, _FakeServer]:
        return self._servers


def test_loads_advertised_specs_as_named_extension() -> None:
    specs = [
        ToolSpec("add", "Add two numbers.", {"type": "object", "properties": {"a": {}, "b": {}}}),
        ToolSpec("subtract", "Subtract one number from another.", {"type": "object", "properties": {}}),
    ]
    server = _FakeServer(specs)

    extension = asyncio.run(tool_server.make_extension("calculator", server))

    assert extension.name == "calculator"
    assert [t.name for t in extension.tools] == ["add", "subtract"]
    add = extension.tools[0]
    assert add.description == "Add two numbers."
    assert add.parameters == {"type": "object", "properties": {"a": {}, "b": {}}}


def test_tool_proxies_call_to_the_server() -> None:
    server = _FakeServer([ToolSpec("shout", "Uppercase.", {})], {"shout": "HELLO"})

    extension = asyncio.run(tool_server.make_extension("echo", server))
    result = asyncio.run(extension.tools[0].execute({"text": "hello"}))

    assert result == "HELLO"
    assert server.calls == [("shout", {"text": "hello"})]


def test_each_tool_proxies_under_its_own_name() -> None:
    specs = [ToolSpec("first", "First.", {}), ToolSpec("second", "Second.", {})]
    server = _FakeServer(specs)

    extension = asyncio.run(tool_server.make_extension("srv", server))
    asyncio.run(extension.tools_by_name()["srv__second"].execute({"x": 1}))

    assert server.calls == [("second", {"x": 1})]


def test_connected_opens_servers_and_yields_extensions() -> None:
    first = _FakeServer([ToolSpec("a", "A.", {})])
    second = _FakeServer([ToolSpec("b", "B.", {})])

    async def run():
        source = _FakeSource({"one": first, "two": second})
        async with tool_server.connected(source) as extensions:
            assert first.connected and second.connected
            return [e.name for e in extensions]

    assert asyncio.run(run()) == ["one", "two"]
    assert first.closed and second.closed


def test_connected_closes_servers_when_the_body_raises() -> None:
    server = _FakeServer([ToolSpec("a", "A.", {})])

    async def run():
        async with tool_server.connected(_FakeSource({"one": server})):
            raise RuntimeError("boom")

    try:
        asyncio.run(run())
    except RuntimeError:
        pass

    assert server.closed
