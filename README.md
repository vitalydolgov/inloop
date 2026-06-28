Agent Loop
==========

A minimal Python implementation of the agentic loop — streaming conversation with a language model that can call tools and act on their results.

## Setup

```sh
uv sync --all-groups
export ANTHROPIC_API_KEY="sk-ant-api..."
uv run demo
```

## Documentation

- [Extensions](docs/extensions.md) — how to create and register tools
