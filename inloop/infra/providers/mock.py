"""Model that replays scripted Markdown replies without calling an API."""

import asyncio
from collections.abc import AsyncIterator, Sequence

from inloop.domain import message
from inloop.domain import streaming
from inloop.domain import tool


class MockModel:
    """A Model that answers each request with the next scripted Markdown reply."""

    def __init__(
        self,
        script: str | Sequence[str],
        chunk_size: int = 6,
        delay: float = 0.0,
    ):
        self._replies = [script] if isinstance(script, str) else list(script)
        self._chunk_size = chunk_size
        self._delay = delay
        self._turn = 0

    async def stream(
        self,
        messages: Sequence[message.Message],
        tools: Sequence[tool.Tool] = (),
    ) -> AsyncIterator[streaming.Event]:
        """Replay the next scripted reply as a stream of text deltas."""
        reply = self._replies[min(self._turn, len(self._replies) - 1)] if self._replies else ""
        self._turn += 1

        if reply:
            yield streaming.TextPhase.STARTED
            for start in range(0, len(reply), self._chunk_size):
                if self._delay:
                    await asyncio.sleep(self._delay)
                yield streaming.TextDelta(reply[start:start + self._chunk_size])
            yield streaming.TextPhase.ENDED

        yield streaming.MessageCompleted(text=reply, stop_reason="end_turn")
