"""Summarizes older turns when a conversation nears the model's context window."""

from collections.abc import Sequence

from inloop.domain import message
from inloop.domain.message import Message, Role
from inloop.domain import model as model_port
from inloop.domain import streaming

DEFAULT_THRESHOLD = 0.9

SUMMARY_INSTRUCTION = (
    "Summarize the conversation so far into a compact briefing that lets you carry "
    "on without the full history. Preserve the goal, the decisions made, the files "
    "and identifiers touched, and any open threads or next steps. Write terse notes, "
    "not prose, and do not address the user."
)

SUMMARY_HEADING = "[Summary of earlier conversation]"


class Compactor:
    """Replaces older turns with a model-written summary as the context fills up."""

    def __init__(self, model: model_port.Model, threshold: float = DEFAULT_THRESHOLD):
        self._model = model
        self._budget = model.context_window * threshold

    def is_full(self, input_tokens: int) -> bool:
        """Report whether the last request has grown past the compaction budget."""
        return input_tokens >= self._budget

    def can_compact(self, history: Sequence[Message]) -> bool:
        """Report whether there is an earlier turn to summarize."""
        return _split_point(history) > 0

    async def compact(self, history: Sequence[Message]) -> list[Message]:
        """Summarize every turn before the latest one, keeping that turn verbatim."""
        split = _split_point(history)
        if split <= 0:
            return list(history)
        older, recent = history[:split], history[split:]
        summary = await self._summarize(older)
        head, *tail = recent
        briefing = f"{SUMMARY_HEADING}\n{summary}\n\n{_text_of(head)}"
        return [Message(Role.USER, [message.Text(briefing)]), *tail]

    async def _summarize(self, older):
        request = [*older, Message(Role.USER, [message.Text(SUMMARY_INSTRUCTION)])]
        async for event in self._model.stream(request):
            if isinstance(event, streaming.MessageCompleted):
                return event.text
        return ""


def _split_point(history):
    for i in range(len(history) - 1, -1, -1):
        msg = history[i]
        if msg.role == Role.USER and any(isinstance(b, message.Text) for b in msg.content):
            return i
    return 0


def _text_of(msg):
    return "\n".join(b.text for b in msg.content if isinstance(b, message.Text))
