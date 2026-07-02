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

- **Context** — assemble what the model sees this step: prompt, transcript, retrieved memory, tool definitions.
- **Observe** — take in the latest input: a user message, or the results of the previous step's actions.
- **Reason** — let the model think about what to do next.
- **Act** — call tools, feed their results back into context, and loop.

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

An extension is a named bundle of tools that the agent can call. Each is a self-contained package — bundled in the [`inloop-builtin`](https://github.com/vitalydolgov/inloop-builtin) submodule under `extensions/`, or living in its own repo — that exposes an `EXTENSION` value describing its tools. Installed extensions are discovered automatically. Writing one means declaring tools with `inloop.contrib` and can be tried out with `uv run probe`, without starting the agent. See [docs/extensions.md](docs/extensions.md) for how to create and install one.

### Bundled extensions

- `calculator` — evaluates arithmetic expressions (a minimal example extension)
- `browser` — drives a Chrome browser for web automation
- `filesystem` — reads, writes, and patches files on disk

### External extensions

- [`ios-simulator`](https://github.com/vitalydolgov/ios-simulator-inloop) — drives an iOS simulator through Appium
- [`newsfeed`](https://github.com/vitalydolgov/newsfeed-inloop) — reads vtech news from multiple sources — Hacker News, etc. — each as its own feed

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

Feed it messages through `agent.events(messages)`, an async generator over `streaming.Event`s — see `demo/main.py` for a full interactive terminal loop.

## Documentation

- [Extensions](docs/extensions.md) — how to create and install extensions
- [Providers](docs/providers.md) — supported LLM backends, how to configure them, and how to write your own
- [Configuration](docs/configuration.md) — environment variables and `.env` settings
- [Ports and adapters](docs/hexagonal.md) — the ports connecting domain and app to their implementations
- [Logging](docs/logging.md) — recording user input, model output, and tool calls
- [Testing](docs/testing.md) — test layout, how to run tests, and what gets covered
- [Telegram](docs/telegram.md) — running the agent as a Telegram bot
