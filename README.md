# Loop

A hackable Python implementation of the agentic loop: a language model streams a conversation, calls tools, and acts on their results. Add your own tools via extensions.

## Extensions

An extension is a named bundle of tools that the agent can call. Each is a self-contained package — bundled under `extensions/` or living in its own repo — that exposes an `EXTENSION` value describing its tools. See [docs/extensions.md](docs/extensions.md) for how to create, install, and register one.

### Built-in extensions

- `calculator` — evaluates arithmetic expressions (a minimal example extension)
- `browser` — drives a Chrome browser for web automation
- `filesystem` — reads, writes, and patches files on disk

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

Install the provider extras, export the matching API key, then run the demo.

Install every provider extra:

```sh
uv sync --all-groups --all-extras
uv run demo
```

Or install just one provider — for example, Anthropic:

```sh
uv sync --all-groups --extra anthropic
export ANTHROPIC_API_KEY=...
uv run demo
```

## Documentation

- [Extensions](docs/extensions.md) — how to create, install, and register extensions
- [Providers](docs/providers.md) — supported LLM backends, how to configure them, and how to write your own
