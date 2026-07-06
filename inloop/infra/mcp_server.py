"""Tool server backed by a Model Context Protocol server, over stdio or HTTP."""

from contextlib import AsyncExitStack

from inloop.domain.tool import ToolSpec
from inloop.infra import app_dirs


class McpToolServer:
    """A ToolServer that speaks the Model Context Protocol to an external server."""

    def __init__(self, *, command=None, args=None, env=None, url=None) -> None:
        self._command = command
        self._args = args or []
        self._env = env
        self._url = url
        self._session = None
        self._stack = AsyncExitStack()

    async def connect(self):
        """Open the transport, start a session, and complete the MCP handshake."""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from mcp.client.streamable_http import streamablehttp_client

        if self._url is not None:
            read, write, _ = await self._stack.enter_async_context(
                streamablehttp_client(self._url)
            )
        else:
            params = StdioServerParameters(
                command=self._command, args=self._args, env=self._env
            )
            log_path = app_dirs.log_dir() / "mcp-server.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            errlog = self._stack.enter_context(open(log_path, "a"))
            read, write = await self._stack.enter_async_context(
                stdio_client(params, errlog=errlog)
            )
        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()

    async def aclose(self):
        """Close the session and its transport."""
        await self._stack.aclose()
        self._session = None

    async def list_tools(self) -> list[ToolSpec]:
        """Return the tools the server advertises."""
        result = await self._session.list_tools()
        return [
            ToolSpec(t.name, t.description or "", t.inputSchema) for t in result.tools
        ]

    async def call_tool(self, name: str, arguments: dict[str, object]) -> str:
        """Call one of the server's tools and return its textual result."""
        result = await self._session.call_tool(name, arguments)
        text = "\n".join(
            block.text for block in result.content if getattr(block, "type", None) == "text"
        )
        return f"[tool error] {text}" if result.isError else text
