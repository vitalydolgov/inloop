"""A user–agent interaction: inbox, multi-pass turns, and cooperative cancel."""

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import aclosing, suppress

from inloop.app import compaction
from inloop.app.conversation import Conversation
from inloop.app.inbox import Inbox
from inloop.app.turn import Turn, TurnResult
from inloop.domain import message
from inloop.domain.message import Message, Role
from inloop.domain import streaming
from inloop.domain import tool

MakeStream = Callable[[], AsyncIterator[streaming.Event]]


class Interaction:
    """Drives the exchange for a stream of user messages until the stream ends."""

    def __init__(
        self,
        messages: AsyncIterator[str],
        tools: dict[str, tool.Tool],
        compactor: compaction.Compactor | None,
        make_stream: MakeStream,
    ):
        self._messages = messages
        self._tools = tools
        self._compactor = compactor
        self._make_stream = make_stream
        self._inbox: Inbox | None = None
        self._bridge = asyncio.Queue()
        self._task: asyncio.Task | None = None

    async def __aenter__(self):
        self._inbox = Inbox(self._messages)
        await self._inbox.__aenter__()
        return self

    async def __aexit__(self, *exc):
        await self._close()
        if self._inbox is not None:
            await self._inbox.__aexit__(*exc)
            self._inbox = None

    def interrupt(self):
        """Stop the current model response as soon as possible."""
        if self._task is not None:
            self._task.cancel()

    async def _close(self):
        if self._task is not None and not self._task.done():
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        self._task = None

    async def __call__(self, conversation: Conversation):
        assert self._inbox is not None
        async for text in self._inbox:
            conversation.add(Message(Role.USER, [message.Text(text)]))
            async for event in self._respond(conversation):
                yield event

    async def _respond(self, conversation):
        while not self._bridge.empty():
            self._bridge.get_nowait()
        self._task = asyncio.create_task(self._run_turns(conversation))
        try:
            while (item := await self._bridge.get()) is not None:
                yield item
        finally:
            await self._close()

    async def _run_turns(self, conversation):
        turn = Turn(
            tools=self._tools,
            compactor=self._compactor,
            make_stream=self._make_stream,
        )
        try:
            while True:
                async with aclosing(turn.events(conversation)) as events:
                    async for event in events:
                        await self._bridge.put(event)
                if turn.result is not TurnResult.CONTINUE:
                    break
                for steer in self._inbox.drain():
                    conversation.add(Message(Role.USER, [message.Text(steer)]))
        except asyncio.CancelledError:
            await self._bridge.put(streaming.Interrupted())
            raise
        finally:
            await self._bridge.put(None)
