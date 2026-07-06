# Ports and Adapters

Ports are `Protocol` interfaces declared in `domain` or `app`. `infra` provides concrete implementations that satisfy them structurally, with no inheritance. Each entry below states the port's purpose, then names its adapter and briefly describes the concrete implementation.

### `Model` — `domain/model.py`

A language model that answers a conversation as an async stream of events. Adapters are `AnthropicModel` (`infra/providers/anthropic.py`) and `OpenAIModel` (`infra/providers/openai.py`) for any OpenAI-compatible backend, including Together AI and Fireworks AI. `MockModel` (`infra/providers/mock.py`) replays a recorded conversation and then echoes the user, useful for testing.

### `ExtensionRegistry` — `app/extensions.py`

Installs, removes, lists, and loads extensions. The adapter is `DirectoryExtensionRegistry` (`infra/directory_registry.py`), which keeps each extension in its own isolated directory under the root path it is given.

### `Logger` — `app/logger.py`

Records entries produced while the agent runs. Each entry is tagged with the id of the agent that produced it (`log(entry, agent_id)`), so a spawned subagent's activity is distinguishable from its parent's. The adapter is `PlainLogger` (`infra/plain_logger.py`), which writes logs to files under the path it is given.

### `Environment` — `app/environment.py`

Describes the ambient facts the agent puts in front of the model as a system prompt, so it doesn't guess them — starting with today's date, which the model would otherwise infer from stale training data. The adapter is `SystemEnvironment` (`infra/system_environment.py`), which assembles the description from the host, currently composing a `Clock` for the date. Further facts are added by extending the adapter, leaving the agent untouched.

### `Clock` — `app/clock.py`

Reports the current calendar date. The adapter is `SystemClock` (`infra/system_clock.py`), which reads today's date from the operating system. Consumed by `SystemEnvironment` to date the environment description.

### `ToolServer` — `app/tool_server_config.py`

A server hosting tools the agent can list and call, such as an MCP server. Implementations provide `connect`/`aclose` lifecycle hooks so the app layer can manage their transport. The adapter is `McpToolServer` (`infra/mcp_server.py`), which speaks the Model Context Protocol over stdio or HTTP.

## Configuration

### `Config` — `app/config.py`

Application configuration composed of a section per concern, currently `agent` and `subagent` (each a `ModelConfig`) and `mcp` (a `ToolServerConfig`). The adapter is `TomlConfig` (`infra/toml_config.py`), which reads all sections from a single TOML file and exposes one sub-config each.

### `ModelConfig` — `app/model_config.py`

Provides the model a role runs on, or none when that role declares no model of its own. The adapter is the `[agent.model]` and `[subagent.model]` sections of `TomlConfig` (`infra/toml_config.py`), which read a `provider` name and its settings from the table and hand them to `create_model` (`infra/providers/factory.py`) to build the `Model`. When `[subagent.model]` is absent, spawned subagents reuse the agent's.

### `TelegramConfig` — `demo/telegram/config.py`

Reads the Telegram bot's token, webhook URL, and the route it listens on. The adapter is the `[telegram]` section of `TomlConfig`.

### `ToolServerConfig` — `app/tool_server_config.py`

Provides the tool servers configured for the agent, keyed by the name each is mounted under; the `connected` context manager consumes it. The adapter is the `[mcp.servers]` section of `TomlConfig` (`infra/toml_config.py`), which builds an `McpToolServer` for each entry.