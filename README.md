# InLoop

A hackable Python implementation of the agentic loop: a language model streams a conversation, calls tools, and acts on their results. Add your own tools via extensions.

## North star

An agent is a language model wrapped in a harness. The model reasons; the harness is everything around it that turns reasoning into sustained, useful action. This is *not* the current state. Today the framework implements the core loop, prompts, and tools; orchestration, security, and memory are still aspirational.

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

## Extensions

An extension is a named bundle of tools that the agent can call. Each is a self-contained package — bundled under `extensions/` or living in its own repo — that exposes an `EXTENSION` value describing its tools. Installed extensions are discovered automatically. See [docs/extensions.md](docs/extensions.md) for how to create and install one.

### Built-in extensions

- `calculator` — evaluates arithmetic expressions (a minimal example extension)
- `browser` — drives a Chrome browser for web automation
- `filesystem` — reads, writes, and patches files on disk

### External extensions

- [`ios-simulator`](https://github.com/vitalydolgov/ios-simulator-inloop) — drives an iOS simulator through Appium

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
uv sync --all-extras
uv run demo
```

Or install just one provider — for example, Anthropic:

```sh
uv sync --extra anthropic
export ANTHROPIC_API_KEY=...
uv run demo
```

## Documentation

- [Extensions](docs/extensions.md) — how to create and install extensions
- [Providers](docs/providers.md) — supported LLM backends, how to configure them, and how to write your own
