Agent Loop
==========

A minimal Python implementation of the agentic loop — streaming conversation with a language model that can call tools and act on their results.

## Example

Running against Gemma 4 31B:

```
% uv run demo
> calculate 40+2
[think...]
The user wants to calculate the sum of 40 and 2.
I should use the calculator__evaluate tool to perform this arithmetic operation.
[...think]
[tool: calculator__evaluate {'expression': '40+2'}]
[done: tool_calls]
40 + 2 = 42
[done: stop]
```

## Setup

Install the extra for your chosen provider, export its API key, then run the demo:

```sh
uv sync --all-groups --extra anthropic
uv run demo
```

## Built-in Extensions

- `calculator` — evaluate arithmetic expressions
- `browser` — control a Chrome browser

## Documentation

- [Extensions](docs/extensions.md) — how to create and register tools
- [Providers](docs/providers.md) — supported LLM backends and how to configure them
