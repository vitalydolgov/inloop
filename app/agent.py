"""Workflow that drives a chat loop over a stream of user messages."""

from collections.abc import AsyncIterator, Iterator, Sequence

from app.conversation import Conversation
from domain import message
from domain.message import Message, Role
from domain import model
from domain import streaming
from domain import extension

COMMANDS = frozenset({"/exit", "/quit"})


class Agent:
    """A chat agent that owns its conversation, runs tools, and streams replies."""

    def __init__(
        self,
        language_model: model.Model,
        extensions: Sequence[extension.Extension] = (),
    ) -> None:
        self._model = language_model
        self._tools = {}
        for ext in extensions:
            self._tools.update(ext.tools_by_name())
        self.conversation = Conversation()
        """The conversation transcript owned by this agent."""

    async def events(
        self, messages: AsyncIterator[str]
    ) -> AsyncIterator[streaming.Event]:
        """Ask the model for each non-command message, running any tools it requests."""
        async for user_text in messages:
            if user_text in COMMANDS:
                return

            self.conversation.add(Message(Role.USER, [message.Text(user_text)]))

            for event in self._agent_turn():
                yield event

    def _agent_turn(self) -> Iterator[streaming.Event]:
        """Stream one assistant turn, running tools until the model finishes."""
        while True:
            calls: list[message.ToolCall] = []
            texts: list[message.Text] = []

            tools = list(self._tools.values())
            for event in self._model.stream(self.conversation.history, tools):
                match event:
                    case streaming.ToolUse():
                        call = message.ToolCall(event.id, event.name, event.input)
                        calls.append(call)
                    case streaming.MessageCompleted() if event.text:
                        texts.append(message.Text(event.text))
                yield event

            results = []
            for call in calls:
                tool = self._tools[call.name]
                results.append(message.ToolResult(call.id, tool.execute(call.input)))

            assistant_blocks: list[message.Block] = [*texts, *calls]
            if assistant_blocks:
                self.conversation.add(Message(Role.ASSISTANT, assistant_blocks))

            if results:
                self.conversation.add(Message(Role.USER, results))
            else:
                break
