"""OpenAI-compatible Chat Completions API adapter."""

import json
from collections.abc import AsyncIterator, Sequence

import openai

from inloop.domain import message
from inloop.domain import streaming
from inloop.domain import tool


def _messages(msgs: Sequence[message.Message]) -> list[dict[str, object]]:
    """Render domain messages as OpenAI chat messages."""
    chat: list[dict[str, object]] = []
    for msg in msgs:
        if msg.role == message.Role.USER:
            chat.extend(_user_turn(msg))
        elif msg.role == message.Role.ASSISTANT:
            chat.append(_assistant_turn(msg))
    return chat


def _user_turn(msg: message.Message) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    texts: list[str] = []
    for block in msg.content:
        match block:
            case message.ToolSuccess(tool_call_id, content) | message.ToolFailure(
                tool_call_id, content
            ):
                if texts:
                    entries.append({"role": "user", "content": "\n".join(texts)})
                    texts = []
                entries.append(
                    {"role": "tool", "tool_call_id": tool_call_id, "content": content}
                )
            case message.Text(text):
                texts.append(text)
    if texts:
        entries.append({"role": "user", "content": "\n".join(texts)})
    return entries


def _assistant_turn(msg: message.Message) -> dict[str, object]:
    text_parts: list[str] = []
    tool_calls: list[dict[str, object]] = []
    for block in msg.content:
        match block:
            case message.Text(text):
                text_parts.append(text)
            case message.ToolCall(id, name, input):
                tool_calls.append(
                    {
                        "id": id,
                        "type": "function",
                        "function": {"name": name, "arguments": json.dumps(input)},
                    }
                )
    entry: dict[str, object] = {
        "role": "assistant",
        "content": "\n".join(text_parts) or None,
    }
    if tool_calls:
        entry["tool_calls"] = tool_calls
    return entry


def _tool_specs(tools: Sequence[tool.Tool]) -> list[dict[str, object]]:
    """Render domain tools as OpenAI function specs."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        }
        for t in tools
    ]


class OpenAIModel:
    """A Model backed by an OpenAI-compatible Chat Completions API."""

    def __init__(
        self,
        client: openai.AsyncOpenAI,
        model: str,
        max_tokens: int,
        context_window: int,
    ) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens
        self._context_window = context_window

    @property
    def identifier(self) -> str:
        """The model's identifier."""
        return self._model

    @property
    def context_window(self) -> int:
        """The most tokens the model accepts in one request, or 0 when unbounded."""
        return self._context_window

    async def stream(
        self,
        messages: Sequence[message.Message],
        tools: Sequence[tool.Tool] = (),
        system: str = "",
    ) -> AsyncIterator[streaming.Event]:
        """Stream a response to the conversation, offering the given tools."""
        chat_messages = _messages(messages)
        if system:
            chat_messages.insert(0, {"role": "system", "content": system})
        kwargs: dict[str, object] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": chat_messages,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            kwargs["tools"] = _tool_specs(tools)

        # index → {id, name, arguments} — arguments accumulate across chunks
        tool_accum: dict[int, dict[str, str]] = {}
        text_parts: list[str] = []
        finish_reason: str | None = None
        input_tokens = 0
        in_thinking = False
        in_text = False

        async for chunk in await self._client.chat.completions.create(**kwargs):
            if chunk.usage:
                input_tokens = chunk.usage.prompt_tokens
            choice = chunk.choices[0] if chunk.choices else None
            if choice is None:
                continue
            if choice.finish_reason:
                finish_reason = choice.finish_reason

            delta = choice.delta
            reasoning = getattr(delta, "reasoning", None)
            if reasoning:
                if in_text:
                    in_text = False
                    yield streaming.TextPhase.ENDED
                if not in_thinking:
                    in_thinking = True
                    yield streaming.ThinkingPhase.STARTED
                yield streaming.ThinkingDelta(reasoning)

            if delta.content:
                if in_thinking:
                    in_thinking = False
                    yield streaming.ThinkingPhase.ENDED
                if not in_text:
                    in_text = True
                    yield streaming.TextPhase.STARTED
                text_parts.append(delta.content)
                yield streaming.TextDelta(delta.content)

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = int(tc.index)
                    if idx not in tool_accum:
                        tool_accum[idx] = {
                            "id": tc.id,
                            "name": tc.function.name,
                            "arguments": "",
                        }
                    tool_accum[idx]["arguments"] += tc.function.arguments

        if in_thinking:
            yield streaming.ThinkingPhase.ENDED
        if in_text:
            yield streaming.TextPhase.ENDED

        for tc_data in tool_accum.values():
            yield streaming.ToolUse(
                id=tc_data["id"],
                name=tc_data["name"],
                input=json.loads(tc_data["arguments"]),
            )

        yield streaming.MessageCompleted(
            text="".join(text_parts),
            stop_reason=finish_reason,
            input_tokens=input_tokens,
        )
