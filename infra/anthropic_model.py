"""Anthropic Messages API adapter."""

from collections.abc import Iterator, Sequence

import anthropic

from domain import message
from domain import streaming

DEFAULT_MODEL = "claude-sonnet-4-5"
DEFAULT_MAX_TOKENS = 1024


class AnthropicModel:
    """A Model backed by Anthropic's Messages API."""

    def __init__(
        self,
        client: anthropic.Anthropic,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    def stream(self, messages: Sequence[message.Message]) -> Iterator[streaming.Event]:
        """Stream a response to the conversation so far."""
        payload = [{"role": m.role.value, "content": m.content} for m in messages]
        text_parts: list[str] = []
        with self._client.messages.stream(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=payload,
        ) as stream:
            for event in stream:
                if event.type == "content_block_delta" and event.delta.type == "text_delta":
                    text_parts.append(event.delta.text)
                    yield streaming.TextDelta(event.delta.text)
            final = stream.get_final_message()

        yield streaming.MessageCompleted(
            text="".join(text_parts),
            stop_reason=final.stop_reason,
        )
