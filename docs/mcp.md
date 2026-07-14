# MCP servers

An [MCP](https://modelcontextprotocol.io) server hosts a set of tools behind a standard protocol. Any MCP server can be wired in with no per-server wrapper: its tools become available under namespace `<server>__<tool>`.

Authentication is not handled yet — configure servers that need no credentials, or ones reachable on the local machine.

## How it works

`ToolServer` defines the interface: list tools and call them. `make_tools` (`app/tool_server.py`) turns any `ToolServer` into namespaced tools (`<server>__<tool>`). `McpToolServer` implements that interface for MCP servers over stdio or HTTP.

Servers are declared in `~/.inloop/mcp.json` using the conventional MCP client format: a top-level `mcpServers` object, each key the name the server mounts under. Use either HTTP or stdio — not both in the same entry:

| Option | Transport | What it is |
| --- | --- | --- |
| `url` | HTTP | Endpoint of a remote MCP server |
| `command` | stdio | Executable that starts the server process |
| `args` | stdio | Arguments passed to `command` |
| `env` | stdio | Optional object of environment variables for the child process |
| `cwd` | stdio | Optional working directory for the child process |

At startup the runtime connects every configured server, offers their tools to the model, and closes the connections on exit.

## Reloading

Ask the agent to reload the tool servers (or let it call `agent__reload` itself) to pick up a change without restarting: `mcp.json` is read again, the servers it now declares are connected, and the previous ones are dropped. The tools the model is offered change from the next turn on, and the conversation carries on as it was. Use it after editing a server's code, adding an entry to `mcpServers`, or removing one. Call the tool alone — not together with other server tools in the same turn.

If a newly configured server fails to connect, the reload reports the error as a tool failure and leaves the servers that were already running in place.

## Examples

The fastest way to try MCP servers is to add one of the examples below to `mcp.json`. HTTP servers need no local tooling; stdio servers rely on `uvx`/`uv` or `npx`, which must be installed on your machine.

### DeepWiki

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

When the agent starts, the server provides these tools:

- `deepwiki__read_wiki_structure` — list documentation topics for a repo
- `deepwiki__read_wiki_contents` — read the generated docs for a repo
- `deepwiki__ask_question` — ask a question about a repo

Try asking the agent:

> What does the FastAPI repository do? Use the deepwiki tools to find out.

### DuckDuckGo web search

Connect the [DuckDuckGo MCP server](https://github.com/nickclyde/duckduckgo-mcp-server) to search the web and fetch page content without an API key.

```json
{
  "mcpServers": {
    "duckduckgo": {
      "command": "uvx",
      "args": ["duckduckgo-mcp-server"]
    }
  }
}
```

When the agent starts, it provides these tools:

- `duckduckgo__search` — search the web and return formatted results
- `duckduckgo__fetch_content` — fetch and parse a webpage

Try asking the agent:

> Search the web for the latest Python release.

### Playwright browser control

Connect a Playwright MCP server such as [`@playwright/mcp`](https://www.npmjs.com/package/@playwright/mcp) to control a browser. This stdio server launches Chrome and exposes browser automation tools.

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp", "--browser", "chrome", "--output-dir", "~/.inloop/log/playwright-mcp"]
    }
  }
}
```

It provides tools like `playwright__browser_navigate`, `playwright__browser_click`, and `playwright__browser_snapshot`. Chrome must be installed on your system, or you can let Playwright download it with `npx playwright install chrome`. Send the output to `~/.inloop/log` so it stays out of the project tree.

### Custom MCP

To write your own server, start from [`template-mcp`](https://github.com/vitalydolgov/template-mcp) — a minimal stdio server with a single `health` tool. Clone it, rename the package, and replace the tool with yours.

Wire a local checkout in with a stdio entry (set `cwd` to the clone path):

```json
{
  "mcpServers": {
    "template": {
      "command": "uv",
      "args": ["run", "serve.py"],
      "cwd": "/path/to/template-mcp"
    }
  }
}
```

It provides the tool named `template__health`.
