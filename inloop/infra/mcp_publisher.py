"""Exposes installed extensions' tools as a Model Context Protocol server over stdio."""

from inloop.domain import extension


class McpToolPublisher:
    """A ToolPublisher that serves installed extensions' tools to MCP clients over stdio."""

    async def run(self, extensions: list[extension.Extension]) -> None:
        """Serve every extension's tools over stdio, namespaced <extension>__<tool>, until the client disconnects."""
        import mcp.types as types
        from mcp.server.lowlevel import Server
        from mcp.server.stdio import stdio_server

        server = Server("inloop")
        tools = {}
        for ext in extensions:
            tools.update(ext.tools_by_name())

        @server.list_tools()
        async def list_tools():
            return [
                types.Tool(name=t.name, description=t.description, inputSchema=t.parameters)
                for t in tools.values()
            ]

        @server.call_tool()
        async def call_tool(name, arguments):
            result = await tools[name].execute(arguments)
            return [types.TextContent(type="text", text=result)]

        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())
