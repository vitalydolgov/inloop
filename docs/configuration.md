# Configuration

Configuration is split across three independent files:

- `config.toml` contains the agent model, the optional subagent model, and Telegram settings.
- `mcp.json` contains the [MCP](https://modelcontextprotocol.io) servers whose tools are available to the agent.
- `AGENTS.md` contains instructions added to the agent's context.

All files are optional. If `config.toml` is absent, its settings use their defaults; if `mcp.json` is absent, no MCP servers are loaded; if `AGENTS.md` is absent, the agent receives no additional instructions.

## File locations

The agent and MCP configuration always come from the user-wide directory. Agent instructions can also come from the working directory:

| File | Location |
| --- | --- |
| Agent, subagent, and Telegram settings | `~/.inloop/config.toml` |
| MCP servers | `~/.inloop/mcp.json` |
| Agent instructions | `./AGENTS.md` or `~/.inloop/AGENTS.md` |

Set `INLOOP_HOME` to use a different directory instead of `~/.inloop` for user-wide settings.

## `config.toml`

The TOML file contains these sections:

- `[agent.model]` — the `provider` the agent runs on and that provider's settings. See [Providers](providers.md).
- `[subagent.model]` — an optional distinct provider for spawned subagents, with the same shape as `[agent.model]`; when omitted, subagents reuse the agent's model. See [Providers](providers.md).
- `[telegram]` — `bot_token` and `webhook_url` for the Telegram bot. See [Telegram](telegram.md).

Example:

```toml
[agent.model]
provider = "anthropic"
model = "claude-sonnet-5"
max_tokens = 64000
context_window = 200000
effort = "medium"

[telegram]
bot_token = "..."
webhook_url = "https://..."
```

## `mcp.json`

MCP servers are declared under the conventional top-level `mcpServers` object. Each key is the name used to mount that server's tools. See [MCP servers](mcp.md) for the supported transports and fields.

Example:

```json
{
  "mcpServers": {
    "deepwiki": {
      "url": "https://mcp.deepwiki.com/mcp"
    }
  }
}
```

## `AGENTS.md`

`AGENTS.md` is a Markdown file containing the instructions that guide the agent for a project or across all projects. Its contents are added to the system prompt when the agent starts, after the runtime facts such as the current date. The same prompt is passed to spawned subagents.

`--instructions=auto` is the default: the runtime uses `./AGENTS.md` when it exists and otherwise uses `~/.inloop/AGENTS.md`. Use `--instructions=user` to skip the working directory file.

The file is read once at startup. Restart the agent after changing it.
