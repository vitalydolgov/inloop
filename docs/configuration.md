# Configuration

Settings are read from environment variables, loaded from a `.env` file if present. Copy `.env.example` to `.env` to get started.

## Options

- `EXTENSIONS_PATH` — directory where installed extensions are stored. Defaults to `var/extensions`. See [Extensions](extensions.md).
- Provider API keys — each provider reads its own key directly from the environment, e.g. `ANTHROPIC_API_KEY`. See [Providers](providers.md).

## Adding an option

Settings are exposed through the `Config` port (`app/config.py`), implemented by `EnvConfig` (`infra/env_config.py`). Add a method to both to read a new one.
