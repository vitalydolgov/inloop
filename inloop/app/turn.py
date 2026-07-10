"""One agent turn: fold a model stream into the conversation, run tools, compact."""

import asyncio
from collections.abc import AsyncIterator, Callable
from enum import Enum

from inloop.app import compaction
from inloop.app.conversation import Conversation
from inloop.domain import message
from inloop.domain.message import Message, Role
from inloop.domain import streaming
from inloop.domain import tool

MakeStream = Callable[[], AsyncIterator[streaming.Event]]


class TurnResult(Enum):
    """How a turn finished, for the outer loop."""

    CONTINUE = "continue"
    DONE = "done"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class Turn:
    """Applies one model reply: collect events, run tools, compact if needed."""

    def __init__(
        self,
        tools: dict[str, tool.Tool],
        compactor: compaction.Compactor | None,
        make_stream: MakeStream,
    ):
        self._tools = tools
        self._compactor = compactor
        self._make_stream = make_stream
        self._result = TurnResult.DONE

    @property
    def result(self) -> TurnResult:
        """Outcome of the last `events` run."""
        return self._result

    async def _execute(self, call):
        tool = self._tools[call.name]
        try:
            content = await tool.execute(call.input)
            return message.ToolSuccess(call.id, content)
        except Exception as error:
            return message.ToolFailure(call.id, f"error: {error}")

    async def _compact_if_needed(self, input_tokens, conversation: Conversation):
        if self._compactor is None or not self._compactor.is_full(input_tokens):
            return
        if not self._compactor.can_compact(conversation.history):
            return
        yield streaming.Compaction.STARTED
        conversation.history = await self._compactor.compact(conversation.history)
        yield streaming.Compaction.ENDED

    async def events(self, conversation: Conversation):
        """Stream one model/tool pass: model, tools, and compaction."""
        self._result = TurnResult.INTERRUPTED
        calls = []
        texts = []
        input_tokens = 0

        try:
            async for event in self._make_stream():
                match event:
                    case streaming.ToolUse(id=id, name=name, input=input):
                        calls.append(message.ToolCall(id, name, input))
                    case streaming.MessageCompleted(text=text):
                        if text:
                            texts.append(message.Text(text))
                        input_tokens = event.input_tokens
                yield event

            results = await asyncio.gather(*(self._execute(call) for call in calls))

            assistant_blocks = [*texts, *calls]
            if assistant_blocks:
                conversation.add(Message(Role.ASSISTANT, assistant_blocks))

            if results:
                conversation.add(Message(Role.USER, results))

            results_tokens = sum(len(r.content) for r in results) // 4  # roughly
            async for event in self._compact_if_needed(input_tokens + results_tokens, conversation):
                yield event
            self._result = TurnResult.CONTINUE if results else TurnResult.DONE
        except Exception as error:
            yield streaming.Failed(str(error))
            self._result = TurnResult.FAILED
