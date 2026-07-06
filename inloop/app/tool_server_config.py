"""Port for a server that hosts callable tools, and the adapter into extensions."""

from contextlib import AsyncExitStack, asynccontextmanager
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


class ToolServerConfig(Protocol):
    """Provides the tool servers configured for the agent, keyed by name."""

    def load(self) -> dict[str, ToolServer]:
        """Return the configured tool servers, keyed by the name each is mounted under."""
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


@asynccontextmanager
async def connected(config: ToolServerConfig):
    """Load the configured tool servers, connect each, yield their extensions, and close them on exit."""
    servers = config.load()
    async with AsyncExitStack() as stack:
        for server in servers.values():
            await server.connect()
            stack.push_async_callback(server.aclose)
        yield [await make_extension(name, server) for name, server in servers.items()]
