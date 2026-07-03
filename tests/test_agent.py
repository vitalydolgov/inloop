"""Tests for the chat agent workflow."""

import asyncio
from collections.abc import AsyncIterator, Sequence

from inloop.app import agent
from inloop.app import logger
from inloop.domain import extension
from inloop.domain import message
from inloop.domain import streaming
from inloop.domain import tool


class _ScriptedModel:
    """A Model that replies with a fixed line per turn and records what it saw."""

    def __init__(self, replies: list[str]) -> None:
        self._replies = iter(replies)
        self.seen: list[list[message.Message]] = []
        self.offered_tools: list[list[tool.Tool]] = []

    async def stream(
        self,
        messages: Sequence[message.Message],
        tools: Sequence[tool.Tool] = (),
    ) -> AsyncIterator[streaming.Event]:
        self.seen.append(list(messages))
        self.offered_tools.append(list(tools))
        reply = next(self._replies)
        yield streaming.TextDelta(reply)
        yield streaming.MessageCompleted(text=reply, stop_reason="end_turn")


class _RaisingModel:
    """A Model whose stream yields once, then raises."""

    async def stream(
        self,
        messages: Sequence[message.Message],
        tools: Sequence[tool.Tool] = (),
    ) -> AsyncIterator[streaming.Event]:
        yield streaming.TextDelta("partial")
        raise RuntimeError("boom")


class _TurnModel:
    """A Model that yields a scripted list of events per turn and records history."""

    def __init__(self, turns: list[list[streaming.Event]]) -> None:
        self._turns = iter(turns)
        self.seen: list[list[message.Message]] = []

    async def stream(
        self,
        messages: Sequence[message.Message],
        tools: Sequence[tool.Tool] = (),
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
        streaming.MessageCompleted(text="one", stop_reason="end_turn"),
        streaming.TextDelta("two"),
        streaming.MessageCompleted(text="two", stop_reason="end_turn"),
    ]


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
        can_spawn=False,
    )

    async def gather() -> None:
        async for _ in chat_agent.events(_stream(["hi"])):
            pass

    asyncio.run(gather())

    namespaced = extension.Extension("test", [weather]).tools_by_name()["test__weather"]
    assert model.offered_tools == [[namespaced]]


def test_offers_builtin_tools_under_their_bare_name() -> None:
    async def run(args: dict[str, object]) -> str:
        return "content"

    reader = tool.Tool("read", "Read a file.", {"type": "object", "properties": {}}, run)
    model = _ScriptedModel(["sure"])
    chat_agent = agent.Agent(model, tools=[reader], can_spawn=False)

    async def gather() -> None:
        async for _ in chat_agent.events(_stream(["hi"])):
            pass

    asyncio.run(gather())

    assert model.offered_tools == [[reader]]


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
        def __init__(self) -> None:
            self._turn = 0
            self.seen: list[list[message.Message]] = []

        async def stream(
            self,
            messages: Sequence[message.Message],
            tools: Sequence[tool.Tool] = (),
        ) -> AsyncIterator[streaming.Event]:
            self.seen.append(list(messages))
            self._turn += 1
            if self._turn == 1:
                yield streaming.ToolUse(id="t1", name="test__add", input={"a": 2, "b": 2})
                yield streaming.MessageCompleted(text="", stop_reason="tool_use")
            else:
                yield streaming.TextDelta("the sum is 4")
                yield streaming.MessageCompleted(
                    text="the sum is 4", stop_reason="end_turn"
                )

    model = _ToolThenAnswer()
    chat_agent = agent.Agent(model, extensions=[extension.Extension("test", [adder])])

    async def gather() -> list[streaming.Event]:
        return [event async for event in chat_agent.events(_stream(["add 2 and 2"]))]

    events = asyncio.run(gather())

    assert ran == [{"a": 2, "b": 2}]
    assert events[-1] == streaming.MessageCompleted(
        text="the sum is 4", stop_reason="end_turn"
    )
    assert model.seen[1] == [
        message.Message(message.Role.USER, [message.Text("add 2 and 2")]),
        message.Message(
            message.Role.ASSISTANT,
            [message.ToolCall("t1", "test__add", {"a": 2, "b": 2})],
        ),
        message.Message(message.Role.USER, [message.ToolResult("t1", "4")]),
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
                streaming.MessageCompleted(text="", stop_reason="tool_use"),
            ],
            [streaming.MessageCompleted(text="done", stop_reason="end_turn")],
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
                message.ToolResult("c1", "first-done"),
                message.ToolResult("c2", "second-done"),
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
                streaming.MessageCompleted(text="let me check", stop_reason="tool_use"),
            ],
            [streaming.MessageCompleted(text="final", stop_reason="end_turn")],
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


class _RecordingLogger:
    """A Logger that records every entry it's given, tagged with the producing agent's id."""

    def __init__(self) -> None:
        self.entries: list[tuple[str, logger.Entry]] = []

    async def log(self, entry: logger.Entry, agent_id: str = "main") -> None:
        self.entries.append((agent_id, entry))


def test_logs_user_input_model_output_and_tool_results() -> None:
    async def ran(args: dict[str, object]) -> str:
        return "4"

    adder = tool.Tool("add", "Add two numbers.", {}, ran)

    class _ToolThenAnswer:
        def __init__(self) -> None:
            self._turn = 0

        async def stream(
            self,
            messages: Sequence[message.Message],
            tools: Sequence[tool.Tool] = (),
        ) -> AsyncIterator[streaming.Event]:
            self._turn += 1
            if self._turn == 1:
                yield streaming.ThinkingDelta("thinking about it")
                yield streaming.ToolUse(id="t1", name="test__add", input={"a": 2, "b": 2})
                yield streaming.MessageCompleted(text="", stop_reason="tool_use")
            else:
                yield streaming.TextDelta("the sum is 4")
                yield streaming.MessageCompleted(
                    text="the sum is 4", stop_reason="end_turn"
                )

    recorder = _RecordingLogger()
    chat_agent = agent.Agent(
        _ToolThenAnswer(),
        extensions=[extension.Extension("test", [adder])],
        logger=recorder,
    )

    async def gather() -> None:
        async for _ in chat_agent.events(_stream(["add 2 and 2"])):
            pass

    asyncio.run(gather())

    assert recorder.entries == [
        ("main", message.Message(message.Role.USER, [message.Text("add 2 and 2")])),
        ("main", streaming.ThinkingDelta("thinking about it")),
        ("main", streaming.ToolUse(id="t1", name="test__add", input={"a": 2, "b": 2})),
        ("main", streaming.MessageCompleted(text="", stop_reason="tool_use")),
        (
            "main",
            message.Message(
                message.Role.ASSISTANT,
                [message.ToolCall("t1", "test__add", {"a": 2, "b": 2})],
            ),
        ),
        ("main", message.Message(message.Role.USER, [message.ToolResult("t1", "4")])),
        ("main", streaming.TextDelta("the sum is 4")),
        ("main", streaming.MessageCompleted(text="the sum is 4", stop_reason="end_turn")),
        (
            "main",
            message.Message(message.Role.ASSISTANT, [message.Text("the sum is 4")]),
        ),
    ]


def _run_and_interrupt(turn: list[streaming.Event], after: int) -> tuple[list[streaming.Event], list[message.Message]]:
    chat_agent = agent.Agent(_TurnModel([turn]))

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
            streaming.MessageCompleted(text="partial more", stop_reason="end_turn"),
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
        message.Message(
            message.Role.ASSISTANT,
            [message.Text(f"partial\n\n{agent.INTERRUPTED_NOTICE}")],
        ),
    ]


def test_interrupt_before_any_text_records_only_the_notice() -> None:
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
        message.Message(
            message.Role.ASSISTANT, [message.Text(agent.INTERRUPTED_NOTICE)]
        ),
    ]


def test_model_error_emits_a_failed_event() -> None:
    chat_agent = agent.Agent(_RaisingModel())

    async def gather() -> list[streaming.Event]:
        return [event async for event in chat_agent.events(_stream(["hi"]))]

    events = asyncio.run(gather())

    assert events == [
        streaming.TextDelta("partial"),
        streaming.Failed("boom"),
    ]


def test_tool_error_emits_a_failed_event() -> None:
    async def explode(args: dict[str, object]) -> str:
        raise RuntimeError("tool broke")

    bad = tool.Tool("bad", "Breaks.", {}, explode)
    model = _TurnModel(
        [
            [
                streaming.ToolUse(id="c1", name="test__bad", input={}),
                streaming.MessageCompleted(text="", stop_reason="tool_use"),
            ],
        ]
    )
    chat_agent = agent.Agent(model, extensions=[extension.Extension("test", [bad])])

    async def gather() -> list[streaming.Event]:
        return [event async for event in chat_agent.events(_stream(["go"]))]

    events = asyncio.run(gather())

    assert events[-1] == streaming.Failed("tool broke")


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
                streaming.MessageCompleted(text="", stop_reason="tool_use"),
            ],
            [streaming.MessageCompleted(text="acknowledged", stop_reason="end_turn")],
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
        message.Message(message.Role.USER, [message.ToolResult("c1", "done")]),
        message.Message(message.Role.USER, [message.Text("actually, focus on X")]),
    ]


def test_steered_message_is_logged() -> None:
    tool_ran = asyncio.Event()

    async def run(args: dict[str, object]) -> str:
        tool_ran.set()
        return "done"

    work = tool.Tool("work", "Work.", {}, run)
    model = _TurnModel(
        [
            [
                streaming.ToolUse(id="c1", name="test__work", input={}),
                streaming.MessageCompleted(text="", stop_reason="tool_use"),
            ],
            [streaming.MessageCompleted(text="ok", stop_reason="end_turn")],
        ]
    )
    recorder = _RecordingLogger()
    chat_agent = agent.Agent(
        model, extensions=[extension.Extension("test", [work])], logger=recorder
    )

    async def messages() -> AsyncIterator[str]:
        yield "start"
        await tool_ran.wait()
        yield "steer me"

    async def gather() -> None:
        async for _ in chat_agent.events(messages()):
            pass

    asyncio.run(gather())

    assert (
        "main",
        message.Message(message.Role.USER, [message.Text("steer me")]),
    ) in recorder.entries


def test_events_can_be_called_again_after_a_tool_turn() -> None:
    async def run(args: dict[str, object]) -> str:
        return "done"

    work = tool.Tool("work", "Work.", {}, run)
    model = _TurnModel(
        [
            [
                streaming.ToolUse(id="c1", name="test__work", input={}),
                streaming.MessageCompleted(text="", stop_reason="tool_use"),
            ],
            [streaming.MessageCompleted(text="first", stop_reason="end_turn")],
            [streaming.MessageCompleted(text="second", stop_reason="end_turn")],
        ]
    )
    chat_agent = agent.Agent(model, extensions=[extension.Extension("test", [work])])

    async def gather() -> list[streaming.Event]:
        async for _ in chat_agent.events(_stream(["go"])):
            pass
        return [event async for event in chat_agent.events(_stream(["again"]))]

    events = asyncio.run(gather())

    assert events == [
        streaming.MessageCompleted(text="second", stop_reason="end_turn"),
    ]


def test_subagent_runs_and_returns_result() -> None:
    model = _TurnModel(
        [
            [
                streaming.ToolUse(id="c1", name="agent__spawn", input={"task": "do it"}),
                streaming.MessageCompleted(text="", stop_reason="tool_use"),
            ],
            [
                streaming.TextDelta("child answer"),
                streaming.MessageCompleted(text="child answer", stop_reason="end_turn"),
            ],
            [streaming.MessageCompleted(text="all done", stop_reason="end_turn")],
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
        message.Role.USER, [message.ToolResult("c1", "child answer")]
    )


def test_subagent_runs_on_the_configured_subagent_model() -> None:
    model = _TurnModel(
        [
            [
                streaming.ToolUse(id="c1", name="agent__spawn", input={"task": "do it"}),
                streaming.MessageCompleted(text="", stop_reason="tool_use"),
            ],
            [streaming.MessageCompleted(text="all done", stop_reason="end_turn")],
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


def test_parent_logs_subagent_events_tagged_with_distinct_id() -> None:
    model = _TurnModel(
        [
            [
                streaming.ToolUse(id="c1", name="agent__spawn", input={"task": "do it"}),
                streaming.MessageCompleted(text="", stop_reason="tool_use"),
            ],
            [
                streaming.TextDelta("child answer"),
                streaming.MessageCompleted(text="child answer", stop_reason="end_turn"),
            ],
            [streaming.MessageCompleted(text="all done", stop_reason="end_turn")],
        ]
    )
    recorder = _RecordingLogger()
    chat_agent = agent.Agent(model, logger=recorder)

    async def gather() -> None:
        async for _ in chat_agent.events(_stream(["delegate"])):
            pass

    asyncio.run(gather())

    assert (
        "main",
        message.Message(message.Role.USER, [message.Text("delegate")]),
    ) in recorder.entries
    assert (
        "sub-1",
        message.Message(message.Role.USER, [message.Text("do it")]),
    ) in recorder.entries
    assert (
        "sub-1",
        streaming.MessageCompleted(text="child answer", stop_reason="end_turn"),
    ) in recorder.entries
    assert {agent_id for agent_id, _ in recorder.entries} == {"main", "sub-1"}


class _ConcurrentModel:
    """A Model that spawns two subagents, then answers each by its task text."""

    def __init__(self, replies: dict[str, str]) -> None:
        self._replies = replies

    async def stream(
        self,
        messages: Sequence[message.Message],
        tools: Sequence[tool.Tool] = (),
    ) -> AsyncIterator[streaming.Event]:
        block = messages[-1].content[0]
        if isinstance(block, message.Text) and block.text in self._replies:
            reply = self._replies[block.text]
            yield streaming.TextDelta(reply)
            yield streaming.MessageCompleted(text=reply, stop_reason="end_turn")
            return
        if any(isinstance(b, message.ToolResult) for m in messages for b in m.content):
            yield streaming.MessageCompleted(text="all done", stop_reason="end_turn")
            return
        yield streaming.ToolUse(id="a", name="agent__spawn", input={"task": "task-a"})
        yield streaming.ToolUse(id="b", name="agent__spawn", input={"task": "task-b"})
        yield streaming.MessageCompleted(text="", stop_reason="tool_use")


def test_concurrent_subagents_are_distinguishable() -> None:
    replies = {"task-a": "answer A", "task-b": "answer B"}
    recorder = _RecordingLogger()
    chat_agent = agent.Agent(_ConcurrentModel(replies), logger=recorder)

    async def gather() -> None:
        async for _ in chat_agent.events(_stream(["delegate"])):
            pass

    asyncio.run(gather())

    assert (
        "sub-1",
        streaming.MessageCompleted(text="answer A", stop_reason="end_turn"),
    ) in recorder.entries
    assert (
        "sub-2",
        streaming.MessageCompleted(text="answer B", stop_reason="end_turn"),
    ) in recorder.entries


class _InterruptingLogger:
    """A Logger that interrupts the agent when a subagent streams its first text."""

    def __init__(self) -> None:
        self.entries: list[tuple[str, logger.Entry]] = []
        self.agent: agent.Agent | None = None
        self._fired = False

    async def log(self, entry: logger.Entry, agent_id: str = "main") -> None:
        self.entries.append((agent_id, entry))
        if not self._fired and agent_id == "sub-1" and isinstance(entry, streaming.TextDelta):
            self._fired = True
            self.agent.interrupt()


def test_interrupt_propagates_to_running_subagent() -> None:
    model = _TurnModel(
        [
            [
                streaming.ToolUse(id="c1", name="agent__spawn", input={"task": "work"}),
                streaming.MessageCompleted(text="", stop_reason="tool_use"),
            ],
            [
                streaming.TextDelta("part one"),
                streaming.TextDelta("part two"),
                streaming.MessageCompleted(text="part one part two", stop_reason="end_turn"),
            ],
            [
                streaming.TextDelta("resuming"),
                streaming.MessageCompleted(text="resuming", stop_reason="end_turn"),
            ],
        ]
    )
    recorder = _InterruptingLogger()
    chat_agent = agent.Agent(model, logger=recorder)
    recorder.agent = chat_agent

    async def gather() -> list[streaming.Event]:
        return [event async for event in chat_agent.events(_stream(["delegate"]))]

    events = asyncio.run(gather())

    assert ("sub-1", streaming.Interrupted()) in recorder.entries
    assert ("sub-1", streaming.TextDelta("part two")) not in recorder.entries
    assert events[-1] == streaming.Interrupted()
