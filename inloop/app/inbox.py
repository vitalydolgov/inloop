"""A message stream buffered into a queue, fed in the background."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress


class Inbox:
    """Buffers a message stream so it can be consumed one message at a time, or drained."""

    def __init__(self, messages: AsyncIterator[str]):
        self._messages = messages
        self._queue = asyncio.Queue()
        self._pump = None

    async def __aenter__(self):
        self._pump = asyncio.create_task(self._run())
        return self

    async def __aexit__(self, *error):
        self._pump.cancel()
        with suppress(asyncio.CancelledError):
            await self._pump

    async def __aiter__(self) -> AsyncIterator[str]:
        while True:
            item = await self._queue.get()
            if item is None:
                return
            yield item

    def drain(self) -> list[str]:
        """Take every message buffered right now, leaving the stream open."""
        texts = []
        while not self._queue.empty():
            item = self._queue.get_nowait()
            if item is None:
                self._queue.put_nowait(None)
                break
            texts.append(item)
        return texts

    async def _run(self):
        async for text in self._messages:
            await self._queue.put(text)
        await self._queue.put(None)
