"""Workflow that drives a chat loop over a stream of user messages."""

from collections.abc import AsyncIterator

from app.conversation import Conversation
from domain import message
from domain import model
from domain import streaming

COMMANDS = frozenset({"/exit", "/quit"})


class Agent:
    """A chat agent that owns its conversation and streams replies."""

    def __init__(self, language_model: model.Model) -> None:
        self._model = language_model
        self.conversation = Conversation()
        """The conversation transcript owned by this agent."""

    async def events(
        self, messages: AsyncIterator[str]
    ) -> AsyncIterator[streaming.Event]:
        """Ask the model for each non-command message, yielding every reply event."""
        async for text in messages:
            if text in COMMANDS:
                return
            self.conversation.add(message.Role.USER, text)
            for event in self._model.stream(self.conversation.history):
                if isinstance(event, streaming.MessageCompleted):
                    self.conversation.add(message.Role.ASSISTANT, event.text)
                yield event
