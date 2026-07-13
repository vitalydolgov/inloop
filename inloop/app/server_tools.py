"""The tools drawn from configured servers, connected for a run and rebuilt on demand."""

from contextlib import suppress

from inloop.app import tool_server
from inloop.app.tool_server import ToolServer
from inloop.app.tool_server_config import ToolServerConfig
from inloop.domain import tool


class ServerTools:
    """Tools from configured servers, rebuildable while the agent keeps running."""

    def __init__(self, config: ToolServerConfig):
        self._config = config
        self._servers: dict[str, ToolServer] = {}
        self._tools: list[tool.Tool] = []

    async def __aenter__(self):
        self._servers, self._tools = await self._open()
        return self

    async def __aexit__(self, *error):
        await _close(self._servers)
        self._servers, self._tools = {}, []

    def tools(self) -> list[tool.Tool]:
        """Return the tools of every connected server, namespaced under that server's name."""
        return list(self._tools)

    def servers(self) -> list[str]:
        """Return the names of the currently connected servers."""
        return list(self._servers)

    async def reload(self):
        """Connect the servers the configuration now declares and drop the previous ones."""
        previous = self._servers
        self._servers, self._tools = await self._open()
        await _close(previous)

    async def _open(self):
        opened = {}
        try:
            for name, server in self._config.load().items():
                await server.connect()
                opened[name] = server
            tools = []
            for name, server in opened.items():
                tools.extend(await tool_server.make_tools(name, server))
        except Exception:
            await _close(opened)  # keep whatever set was live before
            raise
        return opened, tools


async def _close(servers):
    for server in servers.values():
        with suppress(Exception):
            await server.aclose()
