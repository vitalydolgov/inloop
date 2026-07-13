"""Tool server backed by a Model Context Protocol server, over stdio or HTTP."""

import asyncio
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

from inloop.domain.tool import ToolSpec
from inloop.infra import app_dirs


class McpToolServer:
    """A ToolServer that speaks the Model Context Protocol to an external server."""

    def __init__(self, *, command=None, args=None, env=None, cwd=None, url=None) -> None:
        self._command = command
        self._args = args or []
        self._env = env
        self._cwd = cwd
        self._url = url
        self._mcp_session = None
        self._shutdown_signal = asyncio.Event()
        self._serve = None

    async def connect(self):
        """Open the transport, start a session, and complete the MCP handshake."""
        initialized = asyncio.get_running_loop().create_future()
        self._serve = asyncio.create_task(self._start(initialized))
        await initialized

    async def aclose(self):
        """Close the session and its transport."""
        if self._serve is None:
            return
        self._shutdown_signal.set()
        await self._serve
        self._serve = None

    async def list_tools(self) -> list[ToolSpec]:
        """Return the tools the server advertises."""
        mcp_tools = await self._mcp_session.list_tools()
        return [
            ToolSpec(t.name, t.description or "", t.inputSchema)
            for t in mcp_tools.tools
        ]

    async def call_tool(self, name: str, arguments: dict[str, object]) -> str:
        """Call one of the server's tools and return its textual result."""
        result = await self._mcp_session.call_tool(name, arguments)
        text = "\n".join(
            block.text for block in result.content if getattr(block, "type", None) == "text"
        )
        if result.isError:
            raise RuntimeError(text)
        return text

    async def _start(self, initialized: asyncio.Future):
        try:
            async with AsyncExitStack() as stack:
                if self._url is not None:
                    client = streamable_http_client(self._url)
                    read, write, _ = await stack.enter_async_context(client)
                else:
                    params = StdioServerParameters(
                        command=self._command,
                        args=self._args,
                        env=self._env,
                        cwd=self._cwd
                    )
                    log_path = app_dirs.log_dir() / "mcp-server.log"
                    log_path.parent.mkdir(parents=True, exist_ok=True)
                    errlog = stack.enter_context(open(log_path, "a"))
                    client = stdio_client(params, errlog=errlog)
                    read, write = await stack.enter_async_context(client)

                self._mcp_session = await stack.enter_async_context(ClientSession(read, write))
                await self._mcp_session.initialize()
                initialized.set_result(True)
                await self._shutdown_signal.wait()
        except Exception as error:
            if not initialized.done():
                initialized.set_exception(error)
        finally:
            self._mcp_session = None

