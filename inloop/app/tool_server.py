"""Port for a server that hosts callable tools, and adapting one into an extension."""

from typing import Protocol

from inloop.domain import extension
from inloop.domain import tool


class ToolServer(Protocol):
    """A server hosting tools the agent can list and call, such as an MCP server."""

    async def connect(self) -> None:
        """Open any transport or session needed before listing or calling tools."""
        ...

    async def aclose(self) -> None:
        """Release any resources opened by connect()."""
        ...

    async def list_tools(self) -> list[tool.ToolSpec]:
        """Return the tools the server advertises."""
        ...

    async def call_tool(self, name: str, arguments: dict[str, object]) -> str:
        """Call one of the server's tools and return its textual result."""
        ...


def _proxy(server, name):
    async def execute(arguments):
        return await server.call_tool(name, arguments)

    return execute


async def make_extension(name: str, server: ToolServer) -> extension.Extension:
    """Make a named extension that proxies a tool server's advertised tools."""
    tools = [
        tool.Tool(spec.name, spec.description, spec.parameters, _proxy(server, spec.name))
        for spec in await server.list_tools()
    ]
    return extension.Extension(name=name, tools=tools)
