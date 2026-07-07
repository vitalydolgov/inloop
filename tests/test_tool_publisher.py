"""Tests for selecting an installed extension and handing it to a publisher."""

import asyncio

import pytest

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
    """A ToolPublisher that records the extension it was asked to run."""

    def __init__(self) -> None:
        self.served: Extension | None = None

    async def run(self, ext: Extension) -> None:
        self.served = ext


def test_serves_the_named_extension() -> None:
    registry = _FakeRegistry([_extension("calculator"), _extension("weather")])
    publisher = _FakePublisher()

    asyncio.run(tool_publisher.serve(registry, "weather", publisher))

    assert publisher.served is not None
    assert publisher.served.name == "weather"


def test_raises_for_an_unknown_extension() -> None:
    registry = _FakeRegistry([_extension("calculator")])
    publisher = _FakePublisher()

    with pytest.raises(LookupError):
        asyncio.run(tool_publisher.serve(registry, "missing", publisher))

    assert publisher.served is None
