"""Model that replays a recorded conversation, then echoes further input."""

import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path

from inloop.domain import message
from inloop.domain import streaming
from inloop.domain import tool


class MockModel:
    """A Model that replays a recorded conversation's replies, then echoes the user."""

    def __init__(self, path: Path, chunk_size: int = 6, delay: float = 0.0):
        turns = json.loads(path.read_text())
        self._replies = [t["text"] for t in turns if t["role"] == message.Role.ASSISTANT]
        self._chunk_size = chunk_size
        self._delay = delay
        self._turn = 0

    @property
    def identifier(self) -> str:
        """The model's identifier."""
        return "mock"

    @property
    def context_window(self) -> int:
        """The most tokens the model accepts in one request, or 0 when unbounded."""
        return 0

    async def stream(
        self,
        messages: list[message.Message],
        tools: list[tool.Tool] = [],
        system: str = "",
    ) -> AsyncIterator[streaming.Event]:
        """Replay the next recorded reply, or echo the last user message once exhausted."""
        if self._turn < len(self._replies):
            reply = self._replies[self._turn]
        else:
            reply = messages[-1].content[0].text
        self._turn += 1

        if reply:
            yield streaming.TextPhase.STARTED
            for start in range(0, len(reply), self._chunk_size):
                if self._delay:
                    await asyncio.sleep(self._delay)
                yield streaming.TextDelta(reply[start:start + self._chunk_size])
            yield streaming.TextPhase.ENDED

        yield streaming.MessageCompleted(text=reply, stop_reason="end_turn", input_tokens=0)
