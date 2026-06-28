"""Workflow for a multi-turn conversation with the model."""

from collections.abc import Iterator

from domain import message
from domain import model
from domain import streaming


class Conversation:
    """An ongoing exchange that remembers prior turns and streams each reply."""

    def __init__(self, language_model: model.Model) -> None:
        self._model = language_model
        self._history: list[message.Message] = []

    def ask(self, text: str) -> Iterator[streaming.StreamEvent]:
        """Add a user message and stream the assistant's reply, retaining both."""
        self._history.append(message.Message(message.Role.USER, text))
        for event in self._model.stream(self._history):
            if isinstance(event, streaming.MessageCompleted):
                self._history.append(message.Message(message.Role.ASSISTANT, event.text))
            yield event
