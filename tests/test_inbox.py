"""Tests for the background-fed inbox."""

import asyncio

from inloop.app.inbox import Inbox


def test_yields_each_message_then_ends() -> None:
    async def messages():
        yield "first"
        yield "second"

    async def run() -> list[str]:
        async with Inbox(messages()) as inbox:
            return [item async for item in inbox]

    assert asyncio.run(run()) == ["first", "second"]


def test_drain_takes_every_buffered_message() -> None:
    buffered = asyncio.Event()

    async def messages():
        yield "a"
        yield "b"
        buffered.set()

    async def run() -> list[str]:
        async with Inbox(messages()) as inbox:
            await buffered.wait()
            return inbox.drain()

    assert asyncio.run(run()) == ["a", "b"]


def test_drain_leaves_the_stream_terminable() -> None:
    buffered = asyncio.Event()

    async def messages():
        yield "only"
        buffered.set()

    async def run() -> tuple[list[str], list[str]]:
        async with Inbox(messages()) as inbox:
            await buffered.wait()
            drained = inbox.drain()
            remaining = [item async for item in inbox]
            return drained, remaining

    assert asyncio.run(run()) == (["only"], [])
