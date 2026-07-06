# Ports and Adapters

Ports are `Protocol` interfaces declared in `domain` or `app`. `infra` provides concrete implementations that satisfy them structurally, with no inheritance. Each entry below states the port's purpose, then names its adapter and briefly describes the concrete implementation.

### `Model` — `domain/model.py`

A language model that answers a conversation as an async stream of events. The adapter is `AnthropicModel` (`infra/providers/anthropic.py`). `MockModel` (`infra/providers/mock.py`) replays a recorded conversation and then echoes the user, useful for testing.

### `Config` — `app/config.py`

Application configuration composed of a section per concern, currently `mcp` (a `ToolServerSource`). The adapter is `TomlConfig` (`infra/toml_config.py`), which reads all sections from a single TOML file and exposes one sub-config each.

### `TelegramConfig` — `demo/telegram/config.py`

Reads the Telegram bot's token, webhook URL, and the route it listens on. The adapter is the `[telegram]` section of `TomlConfig`.

### `ExtensionRegistry` — `app/extensions.py`

Installs, removes, lists, and loads extensions. The adapter is `DirectoryExtensionRegistry` (`infra/directory_registry.py`), which keeps each extension in its own isolated directory under the root path it is given.

### `Logger` — `app/logger.py`

Records entries produced while the agent runs. Each entry is tagged with the id of the agent that produced it (`log(entry, agent_id)`), so a spawned subagent's activity is distinguishable from its parent's. The adapter is `PlainLogger` (`infra/plain_logger.py`), which writes logs to files under the path it is given.

### `ToolServer` — `app/tool_server.py`

A server hosting tools the agent can list and call, such as an MCP server. Implementations provide `connect`/`aclose` lifecycle hooks so the app layer can manage their transport. The adapter is `McpToolServer` (`infra/mcp_server.py`), which speaks the Model Context Protocol over stdio or HTTP.

### `ToolServerSource` — `app/tool_server.py`

Provides the tool servers configured for the agent, keyed by the name each is mounted under; the `connected` context manager consumes it. The adapter is the `[mcp.servers]` section of `TomlConfig` (`infra/toml_config.py`), which builds an `McpToolServer` for each entry.
