Agent Loop
==========

A minimal Python implementation of the agentic loop — streaming conversation with a language model that can call tools and act on their results.

## Setup

Install the extra for your chosen provider, export its API key, then run the demo:

```sh
uv sync --all-groups --extra anthropic
uv run demo
```

## Documentation

- [Extensions](docs/extensions.md) — how to create and register tools
- [Providers](docs/providers.md) — supported LLM backends and how to configure them
