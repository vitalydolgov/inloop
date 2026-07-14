"""Tests for the chat agent workflow."""

import asyncio
from collections.abc import AsyncIterator

from inloop.app import agent
from inloop.app import system_prompt
from inloop.app import compaction
from inloop.domain import extension
from inloop.domain import message
from inloop.domain import streaming
from inloop.domain import tool


class _ScriptedModel:
    """A Model that replies with a fixed line per turn and records what it saw."""

    context_window = 0

    def __init__(self, replies: list[str]) -> None:
        self._replies = iter(replies)
        self.seen: list[list[message.Message]] = []
        self.offered_tools: list[list[tool.Tool]] = []
        self.systems: list[str] = []

    async def stream(
        self,
        messages: list[message.Message],
        tools: list[tool.Tool] = [],
        system: str = "",
    ) -> AsyncIterator[streaming.Event]:
        self.seen.append(list(messages))
        self.offered_tools.append(list(tools))
        self.systems.append(system)
        reply = next(self._replies)
        yield streaming.TextDelta(reply)
        yield streaming.MessageCompleted(text=reply, stop_reason="end_turn", input_tokens=0)


class _RaisingModel:
    """A Model whose stream yields once, then raises."""

    context_window = 0

    async def stream(
        self,
        messages: list[message.Message],
        tools: list[tool.Tool] = [],
        system: str = "",
    ) -> AsyncIterator[streaming.Event]:
        yield streaming.TextDelta("partial")
        raise RuntimeError("boom")


class _TurnModel:
    """A Model that yields a scripted list of events per turn and records history."""

    context_window = 0

    def __init__(self, turns: list[list[streaming.Event]]) -> None:
        self._turns = iter(turns)
        self.seen: list[list[message.Message]] = []

    async def stream(
        self,
        messages: list[message.Message],
        tools: list[tool.Tool] = [],
        system: str = "",
    ) -> AsyncIterator[streaming.Event]:
        self.seen.append(list(messages))
        for event in next(self._turns):
            yield event


async def _stream(items: list[str]) -> AsyncIterator[str]:
    for item in items:
        yield item


def _collect(messages: list[str], replies: list[str]) -> list[streaming.Event]:
    chat_agent = agent.Agent(_ScriptedModel(replies))

    async def gather() -> list[streaming.Event]:
        return [event async for event in chat_agent.events(_stream(messages))]

    return asyncio.run(gather())


def test_run_streams_events_for_each_message() -> None:
    events = _collect(["hi", "again"], ["one", "two"])

    assert events == [
        streaming.TextDelta("one"),
        streaming.MessageCompleted(text="one", stop_reason="end_turn", input_tokens=0),
        streaming.TextDelta("two"),
        streaming.MessageCompleted(text="two", stop_reason="end_turn", input_tokens=0),
    ]


def test_puts_system_prompt_on_the_model() -> None:
    model = _ScriptedModel(["ok"])
    chat_agent = agent.Agent(model, system_prompt="Today's date is 2026-07-06.")

    async def gather() -> None:
        async for _ in chat_agent.events(_stream(["hi"])):
            pass

    asyncio.run(gather())

    assert model.systems == ["Today's date is 2026-07-06."]


def test_without_system_prompt_sends_empty() -> None:
    model = _ScriptedModel(["ok"])
    chat_agent = agent.Agent(model)

    async def gather() -> None:
        async for _ in chat_agent.events(_stream(["hi"])):
            pass

    asyncio.run(gather())

    assert model.systems == [""]


def test_system_prompt_combines_environment_and_instructions() -> None:
    class _Environment:
        def describe(self) -> str:
            return "Today's date is 2026-07-06."

    class _Instructions:
        def load(self) -> str:
            return "Always use metric units."

    prompt = system_prompt.compose(_Environment(), _Instructions())

    assert prompt == "Today's date is 2026-07-06.\n\nAlways use metric units."


def test_offers_its_tools_to_the_model() -> None:
    async def look_up(args: dict[str, object]) -> str:
        return "sunny"

    weather = tool.Tool(
        name="weather",
        description="Look up the weather.",
        parameters={"type": "object", "properties": {}},
        execute=look_up,
    )
    model = _ScriptedModel(["sure"])
    chat_agent = agent.Agent(
        model,
        extensions=[extension.Extension("test", [weather])],
        _spawn=False,
    )

    async def gather() -> None:
        async for _ in chat_agent.events(_stream(["hi"])):
            pass

    asyncio.run(gather())

    namespaced = extension.Extension("test", [weather]).tools_by_name()["test__weather"]
    assert model.offered_tools == [[namespaced]]


def test_offers_explicit_tools_to_the_model() -> None:
    async def run(args: dict[str, object]) -> str:
        return "ok"

    builtin = tool.Tool(
        name="list",
        description="List a directory.",
        parameters={"type": "object", "properties": {}},
        execute=run,
    )
    model = _ScriptedModel(["sure"])
    chat_agent = agent.Agent(model, tools=[builtin], _spawn=False)

    async def gather() -> None:
        async for _ in chat_agent.events(_stream(["hi"])):
            pass

    asyncio.run(gather())

    assert model.offered_tools == [[builtin]]


def test_runs_requested_tool_and_feeds_result_back() -> None:
    ran: list[dict[str, object]] = []

    async def run(args: dict[str, object]) -> str:
        ran.append(args)
        return "4"

    adder = tool.Tool(
        name="add",
        description="Add two numbers.",
        parameters={"type": "object", "properties": {}},
        execute=run,
    )

    class _ToolThenAnswer:
        context_window = 0

        def __init__(self) -> None:
            self._turn = 0
            self.seen: list[list[message.Message]] = []

        async def stream(
            self,
            messages: list[message.Message],
            tools: list[tool.Tool] = [],
            system: str = "",
        ) -> AsyncIterator[streaming.Event]:
            self.seen.append(list(messages))
            self._turn += 1
            if self._turn == 1:
                yield streaming.ToolUse(id="t1", name="test__add", input={"a": 2, "b": 2})
                yield streaming.MessageCompleted(text="", stop_reason="tool_use", input_tokens=0)
            else:
                yield streaming.TextDelta("the sum is 4")
                yield streaming.MessageCompleted(
                    text="the sum is 4", stop_reason="end_turn", input_tokens=0
                )

    model = _ToolThenAnswer()
    chat_agent = agent.Agent(model, extensions=[extension.Extension("test", [adder])])

    async def gather() -> list[streaming.Event]:
        return [event async for event in chat_agent.events(_stream(["add 2 and 2"]))]

    events = asyncio.run(gather())

    assert ran == [{"a": 2, "b": 2}]
    assert events[-1] == streaming.MessageCompleted(
        text="the sum is 4", stop_reason="end_turn", input_tokens=0
    )
    assert model.seen[1] == [
        message.Message(message.Role.USER, [message.Text("add 2 and 2")]),
        message.Message(
            message.Role.ASSISTANT,
            [message.ToolCall("t1", "test__add", {"a": 2, "b": 2})],
        ),
        message.Message(message.Role.USER, [message.ToolSuccess("t1", "4")]),
    ]


def test_runs_every_tool_requested_in_one_turn() -> None:
    ran: list[tuple[str, dict[str, object]]] = []

    def make(name: str):
        async def run(args: dict[str, object]) -> str:
            ran.append((name, args))
            return f"{name}-done"

        return run

    first = tool.Tool("first", "First.", {}, make("first"))
    second = tool.Tool("second", "Second.", {}, make("second"))
    model = _TurnModel(
        [
            [
                streaming.ToolUse(id="c1", name="test__first", input={"x": 1}),
                streaming.ToolUse(id="c2", name="test__second", input={"y": 2}),
                streaming.MessageCompleted(text="", stop_reason="tool_use", input_tokens=0),
            ],
            [streaming.MessageCompleted(text="done", stop_reason="end_turn", input_tokens=0)],
        ]
    )
    chat_agent = agent.Agent(model, extensions=[extension.Extension("test", [first, second])])

    async def gather() -> None:
        async for _ in chat_agent.events(_stream(["go"])):
            pass

    asyncio.run(gather())

    assert sorted(ran) == [("first", {"x": 1}), ("second", {"y": 2})]
    assert model.seen[1] == [
        message.Message(message.Role.USER, [message.Text("go")]),
        message.Message(
            message.Role.ASSISTANT,
            [
                message.ToolCall("c1", "test__first", {"x": 1}),
                message.ToolCall("c2", "test__second", {"y": 2}),
            ],
        ),
        message.Message(
            message.Role.USER,
            [
                message.ToolSuccess("c1", "first-done"),
                message.ToolSuccess("c2", "second-done"),
            ],
        ),
    ]


def test_assistant_turn_keeps_text_before_tool_calls() -> None:
    async def run(args: dict[str, object]) -> str:
        return "ok"

    only = tool.Tool("only", "Only.", {}, run)
    model = _TurnModel(
        [
            [
                streaming.TextDelta("let me check"),
                streaming.ToolUse(id="c1", name="test__only", input={}),
                streaming.MessageCompleted(text="let me check", stop_reason="tool_use", input_tokens=0),
            ],
            [streaming.MessageCompleted(text="final", stop_reason="end_turn", input_tokens=0)],
        ]
    )
    chat_agent = agent.Agent(model, extensions=[extension.Extension("test", [only])])

    async def gather() -> None:
        async for _ in chat_agent.events(_stream(["go"])):
            pass

    asyncio.run(gather())

    assert chat_agent.conversation.history[1] == message.Message(
        message.Role.ASSISTANT,
        [message.Text("let me check"), message.ToolCall("c1", "test__only", {})],
    )


def test_model_error_emits_a_failed_event() -> None:
    chat_agent = agent.Agent(_RaisingModel())

    async def gather() -> list[streaming.Event]:
        return [event async for event in chat_agent.events(_stream(["hi"]))]

    events = asyncio.run(gather())

    assert events == [
        streaming.TextDelta("partial"),
        streaming.Failed("boom"),
    ]


def test_tool_error_is_reported_as_result() -> None:
    async def explode(args: dict[str, object]) -> str:
        raise RuntimeError("tool broke")

    bad = tool.Tool("bad", "Breaks.", {}, explode)
    model = _TurnModel(
        [
            [
                streaming.ToolUse(id="c1", name="test__bad", input={}),
                streaming.MessageCompleted(text="", stop_reason="tool_use", input_tokens=0),
            ],
            # second turn after receiving the error result
            [streaming.MessageCompleted(text="I see the tool failed.", stop_reason="end_turn", input_tokens=0)],
        ]
    )
    chat_agent = agent.Agent(model, extensions=[extension.Extension("test", [bad])])

    async def gather() -> list[streaming.Event]:
        return [event async for event in chat_agent.events(_stream(["go"]))]

    events = asyncio.run(gather())

    # Final message from model after seeing the tool error result
    assert events[-1] == streaming.MessageCompleted(text="I see the tool failed.", stop_reason="end_turn", input_tokens=0)
    # Tool error becomes a result the model can see
    result_block = next(b for m in chat_agent.conversation.history for b in m.content if isinstance(b, message.ToolFailure))
    assert result_block.content == "error: tool broke"


def test_each_turn_includes_prior_turns() -> None:
    model = _ScriptedModel(["first reply", "second reply"])
    chat_agent = agent.Agent(model)

    async def gather() -> None:
        async for _ in chat_agent.events(_stream(["first question", "second question"])):
            pass

    asyncio.run(gather())

    assert model.seen[0] == [
        message.Message(message.Role.USER, [message.Text("first question")]),
    ]
    assert model.seen[1] == [
        message.Message(message.Role.USER, [message.Text("first question")]),
        message.Message(message.Role.ASSISTANT, [message.Text("first reply")]),
        message.Message(message.Role.USER, [message.Text("second question")]),
    ]


def test_steering_message_injected_between_tool_turns() -> None:
    tool_ran = asyncio.Event()

    async def run(args: dict[str, object]) -> str:
        tool_ran.set()
        return "done"

    work = tool.Tool("work", "Work.", {}, run)
    model = _TurnModel(
        [
            [
                streaming.ToolUse(id="c1", name="test__work", input={}),
                streaming.MessageCompleted(text="", stop_reason="tool_use", input_tokens=0),
            ],
            [streaming.MessageCompleted(text="acknowledged", stop_reason="end_turn", input_tokens=0)],
        ]
    )
    chat_agent = agent.Agent(model, extensions=[extension.Extension("test", [work])])

    async def messages() -> AsyncIterator[str]:
        yield "start the task"
        await tool_ran.wait()
        yield "actually, focus on X"

    async def gather() -> None:
        async for _ in chat_agent.events(messages()):
            pass

    asyncio.run(gather())

    assert model.seen[1] == [
        message.Message(message.Role.USER, [message.Text("start the task")]),
        message.Message(
            message.Role.ASSISTANT, [message.ToolCall("c1", "test__work", {})]
        ),
        message.Message(message.Role.USER, [message.ToolSuccess("c1", "done")]),
        message.Message(message.Role.USER, [message.Text("actually, focus on X")]),
    ]


def test_events_can_be_called_again_after_a_tool_turn() -> None:
    async def run(args: dict[str, object]) -> str:
        return "done"

    work = tool.Tool("work", "Work.", {}, run)
    model = _TurnModel(
        [
            [
                streaming.ToolUse(id="c1", name="test__work", input={}),
                streaming.MessageCompleted(text="", stop_reason="tool_use", input_tokens=0),
            ],
            [streaming.MessageCompleted(text="first", stop_reason="end_turn", input_tokens=0)],
            [streaming.MessageCompleted(text="second", stop_reason="end_turn", input_tokens=0)],
        ]
    )
    chat_agent = agent.Agent(model, extensions=[extension.Extension("test", [work])])

    async def gather() -> list[streaming.Event]:
        async for _ in chat_agent.events(_stream(["go"])):
            pass
        return [event async for event in chat_agent.events(_stream(["again"]))]

    events = asyncio.run(gather())

    assert events == [
        streaming.MessageCompleted(text="second", stop_reason="end_turn", input_tokens=0),
    ]


class _CompactingModel:
    """A Model with a small window whose every reply reports a full context."""

    context_window = 100

    def __init__(self) -> None:
        self.seen: list[list[message.Message]] = []

    async def stream(
        self,
        messages: list[message.Message],
        tools: list[tool.Tool] = [],
        system: str = "",
    ) -> AsyncIterator[streaming.Event]:
        self.seen.append(list(messages))
        last = messages[-1].content[-1]
        if isinstance(last, message.Text) and last.text == compaction.SUMMARY_INSTRUCTION:
            yield streaming.MessageCompleted(text="BRIEFING", stop_reason="end_turn", input_tokens=0)
            return
        yield streaming.MessageCompleted(text="answer", stop_reason="end_turn", input_tokens=90)


def test_compacts_after_a_completed_turn_that_fills_the_window() -> None:
    model = _CompactingModel()
    chat_agent = agent.Agent(model)

    async def gather() -> list[streaming.Event]:
        return [event async for event in chat_agent.events(_stream(["hi", "again"]))]

    events = asyncio.run(gather())

    assert events.index(streaming.Compaction.STARTED) < events.index(streaming.Compaction.ENDED)
    summarized = model.seen[2]
    assert summarized[-1] == message.Message(
        message.Role.USER, [message.Text(compaction.SUMMARY_INSTRUCTION)]
    )
    briefing = chat_agent.conversation.history[0].content[0].text
    assert "BRIEFING" in briefing
    assert briefing.endswith("again")


def test_compacts_between_tool_passes_within_a_turn() -> None:
    async def run(args: dict[str, object]) -> str:
        return "ok"

    work = tool.Tool("work", "Work.", {}, run)

    class _ToolLoopModel:
        context_window = 100

        def __init__(self) -> None:
            self.seen: list[list[message.Message]] = []
            self._step = 0

        async def stream(
            self,
            messages: list[message.Message],
            tools: list[tool.Tool] = [],
            system: str = "",
        ) -> AsyncIterator[streaming.Event]:
            self.seen.append(list(messages))
            last = messages[-1].content[-1]
            if isinstance(last, message.Text) and last.text == compaction.SUMMARY_INSTRUCTION:
                yield streaming.MessageCompleted(text="BRIEFING", stop_reason="end_turn", input_tokens=0)
                return
            self._step += 1
            if self._step == 1:  # first turn: a small, non-filling reply
                yield streaming.MessageCompleted(text="ready", stop_reason="end_turn", input_tokens=10)
            elif self._step == 2:  # second turn, pass one: a filling tool call
                yield streaming.ToolUse(id="c1", name="test__work", input={})
                yield streaming.MessageCompleted(text="", stop_reason="tool_use", input_tokens=90)
            else:  # second turn, pass two: the answer, after compaction
                yield streaming.MessageCompleted(text="done", stop_reason="end_turn", input_tokens=10)

    model = _ToolLoopModel()
    chat_agent = agent.Agent(model, extensions=[extension.Extension("test", [work])])

    async def gather() -> list[streaming.Event]:
        return [event async for event in chat_agent.events(_stream(["setup", "work"]))]

    events = asyncio.run(gather())

    assert streaming.Compaction.ENDED in events
    # The pass after compaction sees a summarized history: briefing, tool call, result.
    after = model.seen[3]
    assert after[0].content[0].text.startswith(compaction.SUMMARY_HEADING)
    assert len(after) == 3


def test_subagent_runs_and_returns_result() -> None:
    model = _TurnModel(
        [
            [
                streaming.ToolUse(id="c1", name="agent__spawn", input={"task": "do it"}),
                streaming.MessageCompleted(text="", stop_reason="tool_use", input_tokens=0),
            ],
            [
                streaming.TextDelta("child answer"),
                streaming.MessageCompleted(text="child answer", stop_reason="end_turn", input_tokens=0),
            ],
            [streaming.MessageCompleted(text="all done", stop_reason="end_turn", input_tokens=0)],
        ]
    )
    chat_agent = agent.Agent(model)

    async def gather() -> None:
        async for _ in chat_agent.events(_stream(["delegate"])):
            pass

    asyncio.run(gather())

    assert model.seen[1] == [
        message.Message(message.Role.USER, [message.Text("do it")]),
    ]
    assert model.seen[2][-1] == message.Message(
        message.Role.USER, [message.ToolSuccess("c1", "child answer")]
    )


def test_subagent_runs_on_the_configured_subagent_model() -> None:
    model = _TurnModel(
        [
            [
                streaming.ToolUse(id="c1", name="agent__spawn", input={"task": "do it"}),
                streaming.MessageCompleted(text="", stop_reason="tool_use", input_tokens=0),
            ],
            [streaming.MessageCompleted(text="all done", stop_reason="end_turn", input_tokens=0)],
        ]
    )
    subagent_model = _ScriptedModel(["child answer"])
    chat_agent = agent.Agent(model, subagent_model=subagent_model)

    async def gather() -> None:
        async for _ in chat_agent.events(_stream(["delegate"])):
            pass

    asyncio.run(gather())

    assert subagent_model.seen == [
        [message.Message(message.Role.USER, [message.Text("do it")])],
    ]


class _ConcurrentModel:
    """A Model that spawns two subagents, then answers each by its task text."""

    context_window = 0

    def __init__(self, replies: dict[str, str]) -> None:
        self._replies = replies

    async def stream(
        self,
        messages: list[message.Message],
        tools: list[tool.Tool] = [],
        system: str = "",
    ) -> AsyncIterator[streaming.Event]:
        block = messages[-1].content[0]
        if isinstance(block, message.Text) and block.text in self._replies:
            reply = self._replies[block.text]
            yield streaming.TextDelta(reply)
            yield streaming.MessageCompleted(text=reply, stop_reason="end_turn", input_tokens=0)
            return
        if any(isinstance(b, message.ToolResult) for m in messages for b in m.content):
            yield streaming.MessageCompleted(text="all done", stop_reason="end_turn", input_tokens=0)
            return
        yield streaming.ToolUse(id="a", name="agent__spawn", input={"task": "task-a"})
        yield streaming.ToolUse(id="b", name="agent__spawn", input={"task": "task-b"})
        yield streaming.MessageCompleted(text="", stop_reason="tool_use", input_tokens=0)


def test_concurrent_subagents_return_their_answers() -> None:
    replies = {"task-a": "answer A", "task-b": "answer B"}
    chat_agent = agent.Agent(_ConcurrentModel(replies))

    async def gather() -> None:
        async for _ in chat_agent.events(_stream(["delegate"])):
            pass

    asyncio.run(gather())

    results = [
        block.content
        for msg in chat_agent.conversation.history
        for block in msg.content
        if isinstance(block, message.ToolSuccess)
    ]
    assert set(results) == {"answer A", "answer B"}


def _run_and_interrupt(
    turn: list[streaming.Event], after: int
) -> tuple[list[streaming.Event], list[message.Message]]:
    class _PausingModel:
        """Yields scripted events, then waits so interrupt can land mid-stream."""

        context_window = 0

        async def stream(
            self,
            messages: list[message.Message],
            tools: list[tool.Tool] = [],
            system: str = "",
        ) -> AsyncIterator[streaming.Event]:
            for index, event in enumerate(turn):
                yield event
                if index + 1 == after:
                    await asyncio.Event().wait()

    chat_agent = agent.Agent(_PausingModel())

    async def gather() -> list[streaming.Event]:
        seen: list[streaming.Event] = []
        async for event in chat_agent.events(_stream(["question"])):
            seen.append(event)
            if len(seen) == after:
                chat_agent.interrupt()
        return seen

    events = asyncio.run(gather())
    return events, chat_agent.conversation.history


def test_interrupt_stops_streaming_and_emits_an_event() -> None:
    events, history = _run_and_interrupt(
        [
            streaming.TextDelta("par"),
            streaming.TextDelta("tial"),
            streaming.TextDelta("more"),
            streaming.MessageCompleted(text="partial more", stop_reason="end_turn", input_tokens=0),
        ],
        after=2,
    )

    assert events == [
        streaming.TextDelta("par"),
        streaming.TextDelta("tial"),
        streaming.Interrupted(),
    ]
    assert history == [
        message.Message(message.Role.USER, [message.Text("question")]),
    ]


def test_interrupt_before_any_text_emits_an_event() -> None:
    events, history = _run_and_interrupt(
        [
            streaming.ThinkingPhase.STARTED,
            streaming.TextDelta("unseen"),
        ],
        after=1,
    )

    assert events == [streaming.ThinkingPhase.STARTED, streaming.Interrupted()]
    assert history == [
        message.Message(message.Role.USER, [message.Text("question")]),
    ]


def test_interrupt_cancels_a_running_tool() -> None:
    started = asyncio.Event()
    tool_cancelled = asyncio.Event()

    async def hang(args: dict[str, object]) -> str:
        started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            tool_cancelled.set()
            raise
        return "unreachable"

    hang_tool = tool.Tool("hang", "Hang.", {}, hang)
    model = _TurnModel(
        [
            [
                streaming.ToolUse(id="c1", name="test__hang", input={}),
                streaming.MessageCompleted(text="", stop_reason="tool_use", input_tokens=0),
            ],
            [streaming.MessageCompleted(text="should not run", stop_reason="end_turn", input_tokens=0)],
        ]
    )
    chat_agent = agent.Agent(
        model, extensions=[extension.Extension("test", [hang_tool])]
    )

    async def run() -> list[streaming.Event]:
        async def consume() -> list[streaming.Event]:
            return [event async for event in chat_agent.events(_stream(["go"]))]

        async def cancel_when_started() -> None:
            await started.wait()
            chat_agent.interrupt()

        events, _ = await asyncio.gather(consume(), cancel_when_started())
        return events

    events = asyncio.run(run())

    assert tool_cancelled.is_set()
    assert events[-1] == streaming.Interrupted()
    assert not any(
        isinstance(block, message.ToolSuccess)
        for msg in chat_agent.conversation.history
        for block in msg.content
    )


def test_interrupt_propagates_to_running_subagent() -> None:
    class _SpawnThenChildModel:
        """Parent spawns a child; the child yields one delta then waits to be cancelled."""

        context_window = 0

        def __init__(self) -> None:
            self.agent: agent.Agent | None = None
            self.child_saw_part_two = False

        async def stream(
            self,
            messages: list[message.Message],
            tools: list[tool.Tool] = [],
            system: str = "",
        ) -> AsyncIterator[streaming.Event]:
            last = messages[-1].content[0]
            if isinstance(last, message.Text) and last.text == "work":
                yield streaming.TextDelta("part one")
                self.agent.interrupt()
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    self.child_saw_part_two = False
                    raise
                self.child_saw_part_two = True
                yield streaming.TextDelta("part two")
                yield streaming.MessageCompleted(
                    text="part one part two", stop_reason="end_turn", input_tokens=0
                )
                return
            if any(isinstance(b, message.ToolResult) for m in messages for b in m.content):
                yield streaming.MessageCompleted(
                    text="resuming", stop_reason="end_turn", input_tokens=0
                )
                return
            yield streaming.ToolUse(id="c1", name="agent__spawn", input={"task": "work"})
            yield streaming.MessageCompleted(text="", stop_reason="tool_use", input_tokens=0)

    model = _SpawnThenChildModel()
    chat_agent = agent.Agent(model)
    model.agent = chat_agent

    async def gather() -> list[streaming.Event]:
        return [event async for event in chat_agent.events(_stream(["delegate"]))]

    events = asyncio.run(gather())

    assert not model.child_saw_part_two
    assert events[-1] == streaming.Interrupted()
