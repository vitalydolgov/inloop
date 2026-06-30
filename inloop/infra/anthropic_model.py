"""Anthropic Messages API adapter."""

from collections.abc import Iterator, Sequence

import anthropic

from inloop.domain import message
from inloop.domain import streaming
from inloop.domain import tool

def _content(blocks: Sequence[message.Block]) -> list[dict[str, object]]:
    """Render domain content blocks as Anthropic message content."""
    parts: list[dict[str, object]] = []
    for block in blocks:
        match block:
            case message.Text(text):
                parts.append({"type": "text", "text": text})
            case message.ToolCall(id, name, input):
                parts.append(
                    {"type": "tool_use", "id": id, "name": name, "input": input}
                )
            case message.ToolResult(tool_call_id, content):
                parts.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_call_id,
                        "content": content,
                    }
                )
    return parts


class AnthropicModel:
    """A Model backed by Anthropic's Messages API."""

    def __init__(
        self,
        client: anthropic.Anthropic,
        model: str,
        max_tokens: int,
        effort: str | None = None,
        thinking_budget: int | None = None,
    ) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens
        self._effort = effort
        self._thinking_budget = thinking_budget

    def stream(
        self,
        messages: Sequence[message.Message],
        tools: Sequence[tool.Tool] = (),
    ) -> Iterator[streaming.Event]:
        """Stream a response to the conversation, offering the given tools."""
        payload = [
            {"role": m.role.value, "content": _content(m.content)} for m in messages
        ]
        tool_specs = [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters,
            }
            for t in tools
        ]
        kwargs: dict[str, object] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": payload,
            "tools": tool_specs,
        }
        if self._effort is not None:
            kwargs["output_config"] = {"effort": self._effort}
        if self._thinking_budget is not None:
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": self._thinking_budget}

        text_parts: list[str] = []
        in_thinking_block = False
        with self._client.messages.stream(**kwargs) as stream:
            for event in stream:
                if event.type == "content_block_start":
                    if event.content_block.type == "thinking":
                        in_thinking_block = True
                        yield streaming.ThinkingPhase.STARTED
                elif event.type == "content_block_stop" and in_thinking_block:
                    in_thinking_block = False
                    yield streaming.ThinkingPhase.ENDED
                elif event.type == "content_block_delta":
                    if event.delta.type == "thinking_delta":
                        yield streaming.ThinkingDelta(event.delta.thinking)
                    elif event.delta.type == "text_delta":
                        text_parts.append(event.delta.text)
                        yield streaming.TextDelta(event.delta.text)
            final = stream.get_final_message()

        for block in final.content:
            if block.type == "tool_use":
                yield streaming.ToolUse(
                    id=block.id,
                    name=block.name,
                    input=dict(block.input),
                )

        yield streaming.MessageCompleted(
            text="".join(text_parts),
            stop_reason=final.stop_reason,
        )
