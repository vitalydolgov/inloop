# Inloop

A hackable Python implementation of the agentic loop: a language model streams a conversation, calls tools or delegates to subagents, and acts on their results. Add your own tools via extensions.

## North star

An agent is a language model wrapped in a harness. The model reasons; the harness is everything around it that turns reasoning into sustained, useful action. This is *not* the current state. Today the framework implements the core loop, prompts, tools and subagents; orchestration, security, and memory are still aspirational.

```
                      AGENT  =  LLM  +  HARNESS

                       ┌────────────────────┐
 ┌───────────────┐     │  CONTEXT  ◀─────┐  │     ┌────────────────┐
 │    PROMPT     │◀───▶│     ▼           │  │◀───▶│ TOOLS & SKILLS │
 └───────────────┘     │  OBSERVE        │  │     └────────────────┘
                       │     ▼           │  │
 ┌───────────────┐     │   REASON        │  │     ┌────────────────┐
 │ ORCHESTRATION │◀───▶│     ▼           │  │◀───▶│ SECURITY &     │
 └───────────────┘     │    ACT  ────────┘  │     │ GOVERNANCE     │
                       └────────────────────┘     └────────────────┘
                                  ▲
                                  │
                                  ▼
                          ┌───────────────┐
                          │    MEMORY     │
                          └───────────────┘
```

At the center is one turn, run over and over until the work is done:

- **Context** — load what the agent knows going in: prompt, memory, relevant background.
- **Observe** — perceive the present state and the outcome of prior actions.
- **Reason** — decide what to do based on those observations.
- **Act** — execute, often via Tools & Skills, producing new results to observe on the next loop.

Around the loop sit the harness capabilities — each a seam where the harness extends or constrains the model:

- **Prompt** — the instructions and framing that shape behavior.
- **Orchestration** — coordination above a single loop: sub-agents, workflows, routing, retries.
- **Tools & Skills** — the actions the agent can take, supplied as extensions.
- **Security & Governance** — the limits on what an action may do: permissions, sandboxing, audit, approval.
- **Memory** — state that outlives a single turn or session: transcripts, profiles, caches.

## Chat interface

Two ways to talk to the agent:

- **CLI** — an interactive terminal chat that streams each reply live as the model generates it.
- **Telegram** — a bot served over a webhook, restricted to a single Telegram user. See [Telegram](docs/telegram.md).

Running the CLI against Gemma 4 31B:

```
> calculate 40+2

⛭ calculator:evaluate {'expression': '40+2'}

40 + 2 = 42
```

With the [Playwright MCP](https://www.npmjs.com/package/@playwright/mcp), you can control the browser:

```
> open example.com

⛭ playwright:browser_navigate {"url": "https://example.com"}

I have opened example.com for you.
```

With the [DuckDuckGo MCP](https://github.com/nickclyde/duckduckgo-mcp-server), you can search for information:

```
> search for the latest stable version of Python and output only the version number

⛭ duckduckgo:search {"query": "latest major version of python 2025 2026 current stable release", "max_results": 5}

3.14
```

## Extensions

An extension is a named bundle of tools that the agent can call. Each is a self-contained package — bundled in the repo under `extensions/`, or living in its own repo — that exposes an `EXTENSION` value describing its tools. It depends only on `inloop-kit`, the small extension toolkit, not the whole framework. Installed extensions are discovered automatically. Writing one means declaring tools with `inloop_kit` and can be tried out with `uv run inloop probe`, without starting the agent. See [Extensions](docs/extensions.md) for how to create and install one.

### Bundled extensions

- `calculator` — evaluates arithmetic expressions (a minimal example extension)

### External extensions

- [`ios-simulator`](https://github.com/vitalydolgov/ios-simulator-inloop) — drives an iOS simulator through Appium
- [`newsfeed`](https://github.com/vitalydolgov/newsfeed-inloop) — reads vtech news from multiple sources — Hacker News, etc. — each as its own feed

### MCP servers

Any [MCP](https://modelcontextprotocol.io) server plugs in as an extension with no per-server code — its tools become agent tools, namespaced `<server>__<tool>`. Declare servers in `inloop.toml`. See [MCP](docs/mcp.md) for remote and local server examples.

## Setup

1. Provide a config file — optional, since defaults apply without one. Copy `inloop.toml.example` to `inloop.toml` for a project-local config, or create `~/.inloop/inloop.toml` to apply it to every run:

   ```sh
   cp inloop.toml.example inloop.toml
   ```

   `INLOOP_HOME` relocates `~/.inloop`, where logs and installed extensions also live. See [Configuration](docs/configuration.md) for the file's sections.

2. Install the providers you want and export the matching API key (or put it in a `.env` file). Each provider is a package extra.

   Install every provider:

   ```sh
   uv sync --all-extras
   ```

   Or install just one provider — for example, Anthropic:

   ```sh
   uv sync --extra anthropic
   export ANTHROPIC_API_KEY=...
   ```

3. Run the agent:

   ```sh
   uv run inloop
   ```

### Install as a command

`uv run inloop` runs from the source tree. To put an `inloop` command on your PATH and run it from anywhere, install it as a uv tool, naming the providers you want as extras:

```sh
uv tool install "inloop[anthropic]"
```

```sh
inloop
```

## Documentation

- [The agent loop](docs/loop.md) — turns, streaming events, steering, interrupts, and subagents
- [Extensions](docs/extensions.md) — how to create and install extensions
- [MCP servers](docs/mcp.md) — how to connect to a local or remote MCP server
- [Providers](docs/providers.md) — supported LLM backends, how to configure them, and how to write your own
- [Configuration](docs/configuration.md) — the `inloop.toml` settings file and its sections
- [Ports and adapters](docs/hexagonal.md) — the ports connecting domain and app to their implementations
- [Logging](docs/logging.md) — recording user input, model output, and tool calls
- [Testing](docs/testing.md) — test layout, how to run tests, and what gets covered
- [Telegram](docs/telegram.md) — running the agent as a Telegram bot
