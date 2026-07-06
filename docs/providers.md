# Providers

A provider is an adapter between the agent and a specific LLM backend. Below are the built-in providers and instructions for writing a new one.

## Selecting a provider

The agent's model is chosen in the [configuration](configuration.md) file. The `[agent.model]` table names a `provider` and carries that provider's settings; `create_model` (`infra/providers/factory.py`) maps the name to a constructor and passes the remaining keys to it. An optional `[subagent.model]` table, same shape, gives spawned subagents a distinct model — when omitted, they reuse the agent's.

```toml
[agent.model]
provider = "anthropic"
model = "claude-sonnet-5"
max_tokens = 64000
effort = "medium"

[subagent.model]
provider = "anthropic"
model = "claude-haiku-4-5"
max_tokens = 32000
```

## Built-in providers

Each provider lives in its own module under `infra/providers/` and is re-exported from `infra/providers/__init__.py`. To use a provider directly, import its module and instantiate the model class with a backend client and the settings it needs. The examples below show this manual initialization for each built-in provider.

### Anthropic

```sh
uv sync --group anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
```

```python
import anthropic
from inloop.infra import providers

model = providers.anthropic.AnthropicModel(
    anthropic.AsyncAnthropic(),
    model="claude-sonnet-5",
    max_tokens=64_000,
    effort="low",
    thinking_budget=32_000,
)
```

`effort` and `thinking_budget` are optional; pass `thinking_budget` to enable extended thinking with a token budget.

### Together AI

```sh
uv sync --group together
export TOGETHER_API_KEY="..."
```

```python
import together
from inloop.infra import providers

model = providers.together.TogetherModel(
    together.AsyncTogether(),
    model="google/gemma-4-31B-it",
    max_tokens=64_000,
)
```

### Mock

Use this provider to test and develop without calling a live backend.

```python
from pathlib import Path
from inloop.infra.providers.mock import MockModel

model = MockModel(Path("conversation.json"), delay=0.01)
```

Replays a scripted conversation from a JSON file. Only the `assistant` turns are used, in order; once they run out, the model echoes the user's last message back.

```json
[
    {"role": "user", "text": "hello"},
    {"role": "assistant", "text": "hi there, how can I help?"}
]
```

## Writing your own provider

A provider is any class that satisfies the `Model` port — a single `stream` method:

```python
def stream(
    self,
    messages: Sequence[message.Message],
    tools: Sequence[tool.Tool] = (),
) -> Iterator[streaming.Event]:
    ...
```

It is a concrete adapter, so it lives in `infra/providers/` (e.g. `infra/providers/openai.py`) and may import the backend SDK freely. Implementing one is three translations:

**1. Domain messages → backend format.** Walk each `Message` and map its content blocks onto whatever shape the backend expects. `infra/providers/together.py` shows this for an OpenAI-style chat API.

**2. Domain tools → backend specs.** Render each `Tool`'s `name`, `description`, and `parameters` (a JSON Schema) into the backend's function/tool format. Only send tools when the list is non-empty.

**3. Backend stream → `streaming.Event`s.** Consume the backend's streamed chunks and yield domain events in order:

- `ThinkingPhase.STARTED` / `ThinkingDelta` / `ThinkingPhase.ENDED` — wrap reasoning output, if the backend exposes it.
- `TextPhase.STARTED` / `TextDelta` / `TextPhase.ENDED` — wrap each chunk of visible answer text.
- `ToolUse(id, name, input)` — one per requested tool call, with `input` decoded to a `dict` (accumulate streamed argument fragments first).
- `MessageCompleted(text, stop_reason)` — emit exactly once, last, with the full concatenated text and the backend's stop reason.

The agent loop reads only these events, so any backend you can stream from will work.

**Wire it in.** Add a branch to `create_model` (`infra/providers/factory.py`) that recognizes your provider's name and builds it from a settings table, importing the backend SDK lazily inside the branch so it stays optional:

```python
case "openai":
    import openai

    from inloop.infra.providers import openai as adapter

    return adapter.OpenAIModel(
        client=openai.AsyncOpenAI(),
        model=settings["model"],
        max_tokens=settings["max_tokens"],
    )
```

The agent can then run on it by naming it in the [configuration](configuration.md) file:

```toml
[agent.model]
provider = "openai"
model = "..."
max_tokens = 64000
```

A `[subagent.model]` table runs spawned subagents on a different provider or settings than the parent — e.g. a lower effort setting for the cheaper, more scoped work a subagent does.

Re-export your module from `infra/providers/__init__.py` guarded by `try`/`except ImportError` so other providers stay usable without it installed:

```python
try:
    from inloop.infra.providers import openai
except ImportError:
    pass
```