"""Together AI Chat Completions API adapter."""

import json
from collections.abc import Iterator, Sequence

import together

from domain import message
from domain import streaming
from domain import tool

DEFAULT_MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
DEFAULT_MAX_TOKENS = 1024


def _messages(msgs: Sequence[message.Message]) -> list[dict[str, object]]:
    """Render domain messages as Together/OpenAI chat messages."""
    result: list[dict[str, object]] = []
    for msg in msgs:
        match msg.role:
            case message.Role.USER:
                texts: list[str] = []
                for block in msg.content:
                    match block:
                        case message.ToolResult(tool_call_id, content):
                            result.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call_id,
                                    "content": content,
                                }
                            )
                        case message.Text(text):
                            texts.append(text)
                if texts:
                    result.append({"role": "user", "content": "\n".join(texts)})
            case message.Role.ASSISTANT:
                calls: list[message.ToolCall] = []
                text_parts: list[str] = []
                for block in msg.content:
                    match block:
                        case message.Text(text):
                            text_parts.append(text)
                        case message.ToolCall() as call:
                            calls.append(call)
                entry: dict[str, object] = {
                    "role": "assistant",
                    "content": "\n".join(text_parts) or None,
                }
                if calls:
                    entry["tool_calls"] = [
                        {
                            "id": c.id,
                            "type": "function",
                            "function": {
                                "name": c.name,
                                "arguments": json.dumps(c.input),
                            },
                        }
                        for c in calls
                    ]
                result.append(entry)
    return result


def _tool_specs(tools: Sequence[tool.Tool]) -> list[dict[str, object]]:
    """Render domain tools as Together/OpenAI function specs."""
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


class TogetherModel:
    """A Model backed by Together AI's Chat Completions API."""

    def __init__(
        self,
        client: together.Together,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    def stream(
        self,
        messages: Sequence[message.Message],
        tools: Sequence[tool.Tool] = (),
    ) -> Iterator[streaming.Event]:
        """Stream a response to the conversation, offering the given tools."""
        kwargs: dict[str, object] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": _messages(messages),
            "stream": True,
        }
        if tools:
            kwargs["tools"] = _tool_specs(tools)

        # index → {id, name, arguments} — arguments accumulate across chunks
        tool_accum: dict[int, dict[str, str]] = {}
        text_parts: list[str] = []
        finish_reason: str | None = None

        for chunk in self._client.chat.completions.create(**kwargs):
            choice = chunk.choices[0] if chunk.choices else None
            if choice is None:
                continue
            if choice.finish_reason:
                finish_reason = choice.finish_reason

            delta = choice.delta
            if delta.content:
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

        for tc_data in tool_accum.values():
            yield streaming.ToolUse(
                id=tc_data["id"],
                name=tc_data["name"],
                input=json.loads(tc_data["arguments"]),
            )

        yield streaming.MessageCompleted(
            text="".join(text_parts),
            stop_reason=finish_reason,
        )
