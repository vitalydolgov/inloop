"""Tests for handing every installed extension to a publisher."""

import asyncio

from inloop.app import tool_publisher
from inloop.domain.extension import Extension


def _extension(name: str) -> Extension:
    return Extension(name=name, tools=[])


class _FakeRegistry:
    """An ExtensionRegistry that loads a fixed set of extensions."""

    def __init__(self, extensions: list[Extension]) -> None:
        self._extensions = extensions

    def load(self) -> list[Extension]:
        return self._extensions


class _FakePublisher:
    """A ToolPublisher that records the extensions it was asked to run."""

    def __init__(self) -> None:
        self.served: list[Extension] | None = None

    async def run(self, extensions: list[Extension]) -> None:
        self.served = extensions


def test_serves_every_installed_extension() -> None:
    registry = _FakeRegistry([_extension("calculator"), _extension("weather")])
    publisher = _FakePublisher()

    asyncio.run(tool_publisher.serve(registry, publisher))

    assert publisher.served is not None
    assert [e.name for e in publisher.served] == ["calculator", "weather"]


def test_serves_nothing_when_no_extensions_are_installed() -> None:
    publisher = _FakePublisher()

    asyncio.run(tool_publisher.serve(_FakeRegistry([]), publisher))

    assert publisher.served == []
