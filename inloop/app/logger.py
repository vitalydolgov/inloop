"""Port for recording everything that happens while the agent runs."""

import functools
from collections.abc import Awaitable, Callable
from typing import Protocol

from inloop.domain.message import Message
from inloop.domain import streaming


Entry = Message | streaming.Event


class Logger(Protocol):
    """Records entries produced while the agent runs."""

    async def log(self, entry: Entry, agent_id: str = "main") -> None:
        """Record one entry, tagged with the id of the agent that produced it."""
        ...


def logged(log: Callable[[Message], Awaitable[None]]):
    """Decorate a conversation's `add` so each recorded message is logged."""

    def decorator(add):
        @functools.wraps(add)
        async def wrapper(message):
            await log(message)
            add(message)

        return wrapper

    return decorator


def logged_stream(log: Callable[[streaming.Event], Awaitable[None]]):
    """Decorate an event stream so each yielded event is logged."""

    def decorator(events):
        @functools.wraps(events)
        async def wrapper(*args, **kwargs):
            async for event in events(*args, **kwargs):
                await log(event)
                yield event

        return wrapper

    return decorator
