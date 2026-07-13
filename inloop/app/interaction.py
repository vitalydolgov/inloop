"""A user–agent interaction: inbox, multi-pass turns, and cooperative cancel."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import aclosing, suppress

from inloop.app import command
from inloop.app import compaction
from inloop.app.conversation import Conversation
from inloop.app.inbox import Inbox
from inloop.app.turn import Turn, TurnResult
from inloop.app.turn_source import TurnSource
from inloop.domain import message
from inloop.domain.message import Message, Role
from inloop.domain import streaming


class Interaction:
    """Drives the exchange for a stream of user messages until the stream ends."""

    def __init__(
        self,
        messages: AsyncIterator[str],
        compactor: compaction.Compactor | None,
        source: TurnSource,
        commands: list[command.Command] = [],
        system_prompt: str = "",
    ):
        self._messages = messages
        self._source = source
        self._compactor = compactor
        self._commands = commands
        self._system_prompt = system_prompt
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
            if self._commands and text.startswith("/"):
                async for event in self._run_command(text):
                    yield event
                continue
            conversation.add(Message(Role.USER, [message.Text(text)]))
            async for event in self._respond(conversation):
                yield event

    async def _run_command(self, text):
        name = text[1:].partition(" ")[0]
        command = None
        for candidate in self._commands:
            if candidate.name == name:
                command = candidate
                break
        if command is None:
            yield streaming.Failed(f"unknown command: /{name}")
            return
        try:
            await command.run()
            yield streaming.CommandCompleted(name)
        except Exception as error:
            yield streaming.Failed(f"/{name} failed: {error}")

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
            source=self._source,
            compactor=self._compactor,
            system_prompt=self._system_prompt,
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
