# Ports and Adapters

Ports are the interfaces through which the application communicates with the outside world. They are declared by the part of the application that needs the capability, using Python `Protocol` interfaces. Adapters provide the capability without becoming a dependency of the port's owner.

Dependencies point toward the core:

- `domain` defines business-facing ports and does not depend on the other layers.
- `app` defines ports for application capabilities and depends on `domain`.
- `infra` supplies adapters for ports owned by `domain` or `app`.
- Composition roots connect adapters to ports.

## Ports and their adapters

### `Model` — `domain/model.py`

Port for generating model responses. The provider adapters translate domain messages and tools into provider requests, then translate streamed provider responses back into domain events. `AnthropicModel` and `OpenAIModel` connect to hosted model APIs; `MockModel` supplies deterministic responses for local runs and tests. They are in `infra/providers/`.

### `Environment` — `app/environment.py`

Port for describing the environment supplied to the model. `SystemEnvironment` (`infra/system_environment.py`) assembles that description from host-level adapters, keeping the application independent of how those facts are obtained.

### `Instructions` — `app/instructions.py`

Port for instructions supplied to the agent's system prompt. `AgentsFile` (`infra/agents_file.py`) reads the selected `AGENTS.md` file.

### `Clock` — `app/clock.py`

Port for reading the current date. `SystemClock` (`infra/system_clock.py`) obtains the date from the operating system.

### `ToolServer` — `app/tool_server.py`

Port for connecting to a server that lists and runs tools. `McpToolServer` (`infra/mcp_server.py`) manages an MCP session and transport, translating tool discovery and calls between the application port and the remote server.

### `FileSystem` — `app/filesystem.py`

Port for listing, reading, writing, and managing files. `LocalFileSystem` (`infra/local_filesystem.py`) maps those operations to paths on the local disk and leaves the application independent of the filesystem library.

### `Config` — `app/config.py`

Port for application configuration. `TomlConfig` (`infra/toml_config.py`) reads the TOML document and exposes its data through the application’s configuration ports, constructing provider-specific objects where needed.

### `ModelConfig` — `app/model_config.py`

Port for obtaining the model assigned to an application role. `TomlConfig` (`infra/toml_config.py`) resolves the configured provider through the provider factory and returns a `Model` adapter.

### `ToolServerConfig` — `app/tool_server_config.py`

Port for loading configured tool servers. `McpJsonConfig` (`infra/mcp_json_config.py`) reads the MCP client document and constructs an `McpToolServer` adapter for each declared server.

### `TelegramConfig`

Port for reading Telegram runtime settings. `TomlConfig` (`infra/toml_config.py`) translates the file-backed settings into the interface consumed by the Telegram runtime.
