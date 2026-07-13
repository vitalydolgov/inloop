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
        self._errors: dict[str, BaseException] = {}

    async def __aenter__(self):
        self._servers, self._tools = await self._open()
        return self

    async def __aexit__(self, *error):
        await _close(self._servers)
        self._servers, self._tools, self._errors = {}, [], {}

    def tools(self) -> list[tool.Tool]:
        """Return the tools of every connected server, namespaced under that server's name."""
        return list(self._tools)

    def servers(self) -> list[str]:
        """Return the names of the currently connected servers."""
        return list(self._servers)

    def errors(self) -> dict[str, BaseException]:
        """Return servers that failed to connect or list tools on the last open."""
        return dict(self._errors)

    async def reload(self):
        """Connect the servers the configuration now declares and drop the previous ones."""
        previous = self._servers
        self._servers, self._tools = await self._open()
        await _close(previous)

    async def _open(self):
        opened = {}
        errors = {}
        for name, server in self._config.load().items():
            try:
                await server.connect()
                opened[name] = server
            except Exception as error:
                errors[name] = error
                with suppress(Exception):
                    await server.aclose()

        tools = []
        for name, server in list(opened.items()):
            try:
                tools.extend(await tool_server.make_tools(name, server))
            except Exception as error:
                errors[name] = error
                del opened[name]
                with suppress(Exception):
                    await server.aclose()

        if not opened and errors:
            raise next(iter(errors.values()))

        self._errors = errors
        return opened, tools


async def _close(servers):
    for server in servers.values():
        with suppress(Exception):
            await server.aclose()
