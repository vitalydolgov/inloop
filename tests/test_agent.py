"""Tests for the chat agent workflow."""

import asyncio
from collections.abc import AsyncIterator, Iterator, Sequence

from app import agent
from domain import message
from domain import streaming


class _ScriptedModel:
    """A Model that replies with a fixed line per turn and records what it saw."""

    def __init__(self, replies: list[str]) -> None:
        self._replies = iter(replies)
        self.seen: list[list[message.Message]] = []

    def stream(self, messages: Sequence[message.Message]) -> Iterator[streaming.Event]:
        self.seen.append(list(messages))
        reply = next(self._replies)
        yield streaming.TextDelta(reply)
        yield streaming.MessageCompleted(text=reply, stop_reason="end_turn")


async def _stream(items: list[str]) -> AsyncIterator[str]:
    for item in items:
        yield item


def _collect(messages: list[str], replies: list[str]) -> list[streaming.Event]:
    chat_agent = agent.Agent(_ScriptedModel(replies))

    async def gather() -> list[streaming.Event]:
        return [event async for event in chat_agent.events(_stream(messages))]

    return asyncio.run(gather())


def test_run_streams_events_for_each_message() -> None:
    events = _collect(["hi", "again"], ["one", "two"])

    assert events == [
        streaming.TextDelta("one"),
        streaming.MessageCompleted(text="one", stop_reason="end_turn"),
        streaming.TextDelta("two"),
        streaming.MessageCompleted(text="two", stop_reason="end_turn"),
    ]


def test_run_stops_on_command() -> None:
    events = _collect(["/exit", "ignored"], ["unused"])

    assert events == []


def test_each_turn_includes_prior_turns() -> None:
    model = _ScriptedModel(["first reply", "second reply"])
    chat_agent = agent.Agent(model)

    async def gather() -> None:
        async for _ in chat_agent.events(_stream(["first question", "second question"])):
            pass

    asyncio.run(gather())

    assert model.seen[0] == [
        message.Message(message.Role.USER, "first question"),
    ]
    assert model.seen[1] == [
        message.Message(message.Role.USER, "first question"),
        message.Message(message.Role.ASSISTANT, "first reply"),
        message.Message(message.Role.USER, "second question"),
    ]
