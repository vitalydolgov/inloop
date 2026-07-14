# Inloop

A hackable Python implementation of the agentic loop with support for MCP servers: a language model streams a conversation, calls tools or delegates to subagents, and acts on their results.

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
- **Tools & Skills** — the actions the agent can take.
- **Security & Governance** — the limits on what an action may do: permissions, sandboxing, audit, approval.
- **Memory** — state that outlives a single turn or session: transcripts, profiles, caches.

## Chat interface

Two ways to talk to the agent:

- **CLI** — an interactive terminal chat that streams each reply live as the model generates it.
- **Telegram** — a bot served over a webhook. See [Telegram](docs/telegram.md) for setup and access control.

You steer in natural language. The agent acts by calling tools — MCP servers and a few built-ins — and you see each call as it happens. Running the CLI against Gemma 4 31B:

```
> list the current directory

⛭ list {}

README.md
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

Harness control goes through the same path. After you change a server's code, ask the agent to reload — it reconnects from the current config and the next turn sees the new tools:

```
> read the magic

⛭ magic:magic {}

42

> reload and read again

⛭ agent:reload {}
⛭ magic:magic {}

abracadabra
```

## MCP servers

Any [MCP](https://modelcontextprotocol.io) server plugs in with no per-server code — its tools become agent tools, namespaced `<server>__<tool>`. Declare servers in `mcp.json`. See [MCP](docs/mcp.md) for remote and local server examples. To write your own, you can start from [`template-mcp`](https://github.com/vitalydolgov/template-mcp).

## Setup

1. Provide configuration files — optional, since defaults apply without them. Copy `config.toml.example` and `mcp.json.example` to `~/.inloop/` for agent and MCP settings. Add instructions for the agent in a local `AGENTS.md` or `~/.inloop/AGENTS.md`:

   ```sh
   mkdir -p ~/.inloop
   cp config.toml.example ~/.inloop/config.toml
   cp mcp.json.example ~/.inloop/mcp.json
   ```

   `INLOOP_HOME` relocates `~/.inloop`, where logs also live. Run `inloop --instructions=user` to use its `AGENTS.md` instead of local instructions. See [Configuration](docs/configuration.md) for the files' contents and locations.

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

## Subcommands

`inloop` without a subcommand runs the agent loop, the subcommands cover the surrounding tasks:

| Subcommand | Options | What it does |
| --- | --- | --- |
| `telegram-demo` | | Serve the agent as a Telegram bot — see [Telegram](docs/telegram.md) |

## Documentation

- [The agent loop](docs/loop.md) — turns, streaming events, steering, interrupts, and subagents
- [Built-in tools](docs/builtin.md) — local filesystem operations available to the agent
- [MCP servers](docs/mcp.md) — how to connect to a local or remote MCP server
- [Providers](docs/providers.md) — supported LLM backends, how to configure them, and how to write your own
- [Configuration](docs/configuration.md) — the `config.toml`, `mcp.json`, and `AGENTS.md` files
- [Ports and adapters](docs/hexagonal.md) — the ports connecting domain and app to their implementations
- [Testing](docs/testing.md) — test layout, how to run tests, and what gets covered
- [Telegram](docs/telegram.md) — running the agent as a Telegram bot
