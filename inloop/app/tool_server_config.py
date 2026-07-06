"""Port for loading configured tool servers, and connecting them for a run."""

from contextlib import AsyncExitStack, asynccontextmanager
from typing import Protocol

from inloop.app.tool_server import ToolServer, make_extension


class ToolServerConfig(Protocol):
    """Provides the tool servers configured for the agent, keyed by name."""

    def load(self) -> dict[str, ToolServer]:
        """Return the configured tool servers, keyed by the name each is mounted under."""
        ...


@asynccontextmanager
async def connected(config: ToolServerConfig):
    """Load the configured tool servers, connect each, yield their extensions, and close them on exit."""
    servers = config.load()
    async with AsyncExitStack() as stack:
        for server in servers.values():
            await server.connect()
            stack.push_async_callback(server.aclose)
        yield [await make_extension(name, server) for name, server in servers.items()]
