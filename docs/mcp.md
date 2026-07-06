# MCP servers

An [MCP](https://modelcontextprotocol.io) server hosts a set of tools behind a standard protocol. Because that is the same shape as an extension, any MCP server can be wired in as an extension with no per-server wrapper: point the loader at the server and its tools become available under namespace `<server>__<tool>`.

Authentication is not handled yet — configure servers that need no credentials, or ones reachable on the local machine.

## How it works

`ToolServer` defines the interface: list tools and call them. `make_extension` turns any `ToolServer` into an `Extension`, namespacing its tools as `<server>__<tool>`. `McpToolServer` implements that interface for MCP servers over stdio or HTTP.

Servers are declared under the `[mcp.servers]` table of the [configuration](configuration.md) file. Each entry is keyed by the name the server mounts under and carries either a `url` for the HTTP transport or a `command` and `args` for stdio. When no servers are declared, the agent runs with only its installed extensions. At startup the runtime connects every configured server, offers their tools to the model alongside the installed extensions, and closes the connections on exit.

## Examples

The fastest way to try MCP servers is to add one of the examples below to `inloop.toml`. HTTP servers need no local tooling; stdio servers rely on `uvx`/`uv` or `npx`, which must be installed on your machine.

### DeepWiki

[DeepWiki](https://deepwiki.com) is a public, online MCP server that hosts AI-generated documentation for GitHub repositories. It needs no authentication and is a convenient way to test the HTTP transport.

```toml
[mcp.servers.deepwiki]
url = "https://mcp.deepwiki.com/mcp"
```

When the agent starts, the server is loaded as the `deepwiki` extension with these tools:

- `deepwiki__read_wiki_structure` — list documentation topics for a repo
- `deepwiki__read_wiki_contents` — read the generated docs for a repo
- `deepwiki__ask_question` — ask a question about a repo

Try asking the agent:

> What does the FastAPI repository do? Use the deepwiki tools to find out.

### DuckDuckGo web search

Connect the [DuckDuckGo MCP server](https://github.com/nickclyde/duckduckgo-mcp-server) to search the web and fetch page content without an API key.

```toml
[mcp.servers.duckduckgo]
command = "uvx"
args = ["duckduckgo-mcp-server"]
```

When the agent starts, it loads as the `duckduckgo` extension with these tools:

- `duckduckgo__search` — search the web and return formatted results
- `duckduckgo__fetch_content` — fetch and parse a webpage

Try asking the agent:

> Search the web for the latest Python release.

### Playwright browser control

Connect a Playwright MCP server such as [`@playwright/mcp`](https://www.npmjs.com/package/@playwright/mcp) to control a browser. This stdio server launches Chrome and exposes browser automation tools.

```toml
[mcp.servers.playwright]
command = "npx"
args = ["-y", "@playwright/mcp", "--browser", "chrome", "--output-dir", "~/.inloop/log/playwright-mcp"]
```

When the agent starts, it loads as the `playwright` extension with tools like `playwright__browser_navigate`, `playwright__browser_click`, and `playwright__browser_snapshot`. Chrome must be installed on your system, or you can let Playwright download it with `npx playwright install chrome`. Send the output to `~/.inloop/log` so it stays out of the project tree.

### Custom MCP

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

Wire it in with a stdio entry:

```toml
[mcp.servers.testmcp]
command = "uv"
args = ["run", "testmcp_echo.py"]
```

When the agent starts, it loads as the `testmcp` extension with the tool named `testmcp__echo`.
