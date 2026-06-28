agent-loop
==========

Minimal uv Python project using Anthropic's Messages API.

## Packages

- `domain`: domain model
- `infra`: adapters, including the Anthropic Messages API adapter
- `demo`: executable example

## Setup

```sh
uv sync
export ANTHROPIC_API_KEY="your-api-key"
uv run demo
```

The example entrypoint is in `demo/main.py`.
