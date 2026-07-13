"""Port for a server that hosts callable tools, and adapting one into tools."""

from typing import Protocol

from inloop.domain.tool import Tool, ToolSpec


class ToolServer(Protocol):
    """A server hosting tools the agent can list and call, such as an MCP server."""

    async def connect(self) -> None:
        """Open any transport or session needed before listing or calling tools."""
        ...

    async def aclose(self) -> None:
        """Release any resources opened by connect()."""
        ...

    async def list_tools(self) -> list[ToolSpec]:
        """Return the tools the server advertises."""
        ...

    async def call_tool(self, name: str, arguments: dict[str, object]) -> str:
        """Call one of the server's tools and return its textual result."""
        ...


def _proxy(server, name):
    async def execute(arguments):
        return await server.call_tool(name, arguments)

    return execute


async def make_tools(prefix: str, server: ToolServer) -> list[Tool]:
    """Make namespaced tools that proxy a tool server's advertised tools."""
    tools = []
    for server_tool in await server.list_tools():
        qualified = f"{prefix}__{server_tool.name}"
        tool = Tool(
            qualified,
            server_tool.description,
            server_tool.parameters,
            _proxy(server, server_tool.name)
        )
        tools.append(tool)
    return tools
