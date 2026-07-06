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
- **Telegram** — a bot served over a webhook, restricted to a single Telegram user. See [docs/telegram.md](docs/telegram.md).

Running the CLI against Gemma 4 31B:

```
> calculate 40+2

The user wants to calculate the sum of 40 and 2.
I should use the calculator__evaluate tool to perform this arithmetic operation.

⛭ calculator__evaluate {'expression': '40+2'}

40 + 2 = 42
```

## Extensions

An extension is a named bundle of tools that the agent can call. Each is a self-contained package — bundled in the [`inloop-builtin`](https://github.com/vitalydolgov/inloop-builtin) submodule under `extensions/`, or living in its own repo — that exposes an `EXTENSION` value describing its tools. It depends only on `inloop-kit`, the small extension toolkit, not the whole framework. Installed extensions are discovered automatically. Writing one means declaring tools with `inloop_kit` and can be tried out with `uv run probe`, without starting the agent. See [docs/extensions.md](docs/extensions.md) for how to create and install one.

### Bundled extensions

- `calculator` — evaluates arithmetic expressions (a minimal example extension)
- `resources` — reads, writes, and patches local files, and fetches the readable text content of a web page over HTTP

### External extensions

- [`ios-simulator`](https://github.com/vitalydolgov/ios-simulator-inloop) — drives an iOS simulator through Appium
- [`newsfeed`](https://github.com/vitalydolgov/newsfeed-inloop) — reads vtech news from multiple sources — Hacker News, etc. — each as its own feed

### MCP servers

Any [MCP](https://modelcontextprotocol.io) server plugs in as an extension with no per-server code — its tools become agent tools, namespaced `<server>__<tool>`. Declare servers in `mcp.json`; see [docs/mcp.md](docs/mcp.md).

## Setup

1. Fetch the bundled extensions, which live in the [`inloop-builtin`](https://github.com/vitalydolgov/inloop-builtin) submodule:

   ```sh
   git submodule update --init
   ```

2. Copy `.env.example` to `.env` and adjust as needed:

   ```sh
   cp .env.example .env
   ```

3. Install the provider groups and export the matching API key.

   Install every provider:

   ```sh
   uv sync --all-groups
   ```

   Or install just one provider — for example, Anthropic:

   ```sh
   uv sync --group anthropic
   export ANTHROPIC_API_KEY=...
   ```

4. Run the demo:

   ```sh
   uv run demo
   ```

## Quickstart

Wire the pieces together to drive an agent from your own code — this is what `demo/main.py` does to power the CLI:

```python
import pathlib
import anthropic

from inloop.app.agent import Agent
from inloop.infra.directory_registry import DirectoryExtensionRegistry
from inloop.infra import providers

client = anthropic.AsyncAnthropic()
registry = DirectoryExtensionRegistry(pathlib.Path("var/extensions"))
agent = Agent(
    model=providers.anthropic.AnthropicModel(
        client,
        model="claude-sonnet-5",
        max_tokens=64_000,
        effort="medium",
    ),
    subagent_model=providers.anthropic.AnthropicModel(
        client,
        model="claude-sonnet-5",
        max_tokens=64_000,
        effort="low",
    ),
    extensions=registry.load(),
)
```

Drive it with `agent.events(messages)`: feed in an async stream of user messages and render the async stream of `streaming.Event`s it yields back. See `demo/main.py` for a full interactive terminal loop, and [docs/loop.md](docs/loop.md) for how turns, steering, interrupts, and subagents fit together.

## Documentation

- [The agent loop](docs/loop.md) — turns, streaming events, steering, interrupts, and subagents
- [Extensions](docs/extensions.md) — how to create and install extensions
- [MCP servers](docs/mcp.md) — how to connect to a local or remote MCP server
- [Providers](docs/providers.md) — supported LLM backends, how to configure them, and how to write your own
- [Configuration](docs/configuration.md) — environment variables and `.env` settings
- [Ports and adapters](docs/hexagonal.md) — the ports connecting domain and app to their implementations
- [Logging](docs/logging.md) — recording user input, model output, and tool calls
- [Testing](docs/testing.md) — test layout, how to run tests, and what gets covered
- [Telegram](docs/telegram.md) — running the agent as a Telegram bot
