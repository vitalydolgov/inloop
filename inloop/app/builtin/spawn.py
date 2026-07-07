"""Built-in tool for delegating a scoped task to a fresh subagent."""

from collections.abc import Awaitable, Callable

from inloop.domain.tool import Tool

NAME = "agent__spawn"

DESCRIPTION = (
    "Delegate a scoped task to a fresh subagent and return its final answer. "
    "The subagent runs its own conversation with the same tools and reports back."
)

PARAMETERS = {
    "type": "object",
    "properties": {
        "task": {
            "type": "string",
            "description": "The task for the subagent to carry out.",
        }
    },
    "required": ["task"],
}


def spawn_tool(spawn: Callable[[dict[str, object]], Awaitable[str]]) -> Tool:
    """Return the subagent spawn tool backed by the given spawn callable."""
    return Tool(name=NAME, description=DESCRIPTION, parameters=PARAMETERS, execute=spawn)
