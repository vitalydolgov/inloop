"""Reconnect configured tool servers via a built-in tool."""

from inloop.app.server_tools import ServerTools
from inloop.domain import tool

TOOL_NAME = "agent__reload"

_DESCRIPTION = (
    "Reconnect the configured tool servers from the current configuration. "
    "Drops previous connections; the tools of the newly connected servers are "
    "available on the next turn. Call this alone, not together with other server tools."
)

_PARAMETERS: dict[str, object] = {
    "type": "object",
    "properties": {},
}


def make_tool(server_tools: ServerTools) -> tool.Tool:
    """The `agent__reload` tool that rebuilds the live server tool set."""

    async def execute(args: dict[str, object]) -> str:
        await server_tools.reload()
        names = server_tools.servers()
        if not names:
            return "reconnected: no servers configured"
        return "reconnected: " + ", ".join(names)

    return tool.Tool(TOOL_NAME, _DESCRIPTION, _PARAMETERS, execute)
