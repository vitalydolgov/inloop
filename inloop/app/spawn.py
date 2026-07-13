"""Delegate a task to a subagent via the built-in spawn tool."""

from collections.abc import Callable

from inloop.domain.runnable import Runnable
from inloop.domain import streaming
from inloop.domain import tool

INTERRUPTED_NOTICE = "[Interrupted by user]"

TOOL_NAME = "agent__spawn"

_DESCRIPTION = (
    "Delegate a scoped task to a fresh subagent and return its final answer. "
    "The subagent runs its own conversation with the same tools and reports back."
)

_PARAMETERS = {
    "type": "object",
    "properties": {
        "task": {
            "type": "string",
            "description": "The task for the subagent to carry out.",
        }
    },
    "required": ["task"],
}

MakeChild = Callable[[], Runnable]


class Spawner:
    """Builds the spawn tool and tracks running children."""

    def __init__(self, make_child: MakeChild):
        self._make_child = make_child
        self._children: list[Runnable] = []

    @property
    def children(self) -> list[Runnable]:
        """Subagents currently running under this spawner."""
        return self._children

    def tool(self) -> tool.Tool:
        """The `agent__spawn` tool that delegates to a fresh child."""
        return tool.Tool(TOOL_NAME, _DESCRIPTION, _PARAMETERS, self.execute)

    async def execute(self, args: dict[str, object]) -> str:
        """Run a child on the task and return its final answer."""
        child = self._make_child()
        self._children.append(child)
        try:
            return await _run_child(child, str(args["task"]))
        finally:
            self._children.remove(child)


async def _run_child(child, task):
    final = ""

    async def once(text):
        yield text

    async for event in child.events(once(task)):
        match event:
            case streaming.MessageCompleted(text) if text:
                final = text
            case streaming.Failed(error):
                return f"[subagent failed: {error}]"
            case streaming.Interrupted():
                return final or INTERRUPTED_NOTICE
    return final
