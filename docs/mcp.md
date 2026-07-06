# MCP servers

An [MCP](https://modelcontextprotocol.io) server hosts a set of tools behind a standard protocol. Because that is the same shape as an extension, any MCP server can be wired in as an extension with no per-server wrapper: point the loader at the server and its tools become available under namespace `<server>__<tool>`.

Authentication is not handled yet — configure servers that need no credentials, or ones reachable on the local machine.

## How it works

`ToolServer` defines the interface: list tools and call them. `make_extension` turns any `ToolServer` into an `Extension`, namespacing its tools as `<server>__<tool>`. `McpToolServer` implements that interface for MCP servers over stdio or HTTP.

Servers are declared in a JSON file — `mcp.json` by default, overridable with `INLOOP_MCP_CONFIG`. The format matches the `mcpServers` object used by other MCP clients. Copy `mcp.json.example` to `mcp.json` and keep the servers you want. When the file is absent, no MCP servers load and the agent runs with only its installed extensions. At startup the runtime connects every configured server, offers their tools to the model alongside the installed extensions, and closes the connections on exit.

## Example: DeepWiki

[DeepWiki](https://deepwiki.com) is a public, online MCP server that hosts AI-generated documentation for GitHub repositories. It needs no authentication and is a convenient way to test the HTTP transport.

```json
{
  "mcpServers": {
    "deepwiki": {
      "url": "https://mcp.deepwiki.com/mcp"
    }
  }
}
```

When the agent starts, the server is loaded as the `deepwiki` extension with these tools:

- `deepwiki__read_wiki_structure` — list documentation topics for a repo
- `deepwiki__read_wiki_contents` — read the generated docs for a repo
- `deepwiki__ask_question` — ask a question about a repo

Try asking the agent:

> What does the FastAPI repository do? Use the deepwiki tools to find out.

## Example: local echo server

The example server below is not included in the repository; save it to a file such as `testmcp_echo.py`. It exposes a single `echo` tool useful for checking that the wiring works without relying on an internet connection.

```python
import asyncio

from mcp.server import FastMCP

mcp = FastMCP("inloop-test")


@mcp.tool()
def echo(text: str) -> str:
    return text


if __name__ == "__main__":
    asyncio.run(mcp.run_stdio_async())
```

Wire it into `mcp.json` with a stdio entry:

```json
{
  "mcpServers": {
    "testmcp": {
      "command": "uv",
      "args": ["run", "testmcp_echo.py"]
    }
  }
}
```

When the agent starts, it loads as the `testmcp` extension with the tool named `testmcp__echo`.
