# Providers

Supported LLM backends and how to configure them.

A provider is an adapter that lets the agent talk to a specific LLM backend. The agent depends only on the `domain.model.Model` port, so adding a backend never touches `domain` or `app` — see [Writing your own provider](#writing-your-own-provider).

## Built-in providers

Each provider lives in its own module under `inloop/infra/providers/` and is re-exported from `inloop/infra/providers/__init__.py`. Import the `providers` package and reach a given backend off it:

```python
from inloop.infra import providers
```

### Anthropic

```sh
uv sync --extra anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
```

```python
import anthropic
from inloop.infra import providers

model = providers.anthropic.AnthropicModel(
    anthropic.Anthropic(),
    model="claude-sonnet-5",
    max_tokens=64_000,
    effort="low"
)
```

### Together AI

```sh
uv sync --extra together
export TOGETHER_API_KEY="..."
```

```python
import together
from inloop.infra import providers

model = providers.together.TogetherModel(
    together.Together(),
    model="google/gemma-4-31B-it",
    max_tokens=64_000,
)
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

**Wire it in.** Construct your provider and hand it to the `Agent`:

```python
import openai
from inloop.infra import providers

model = providers.openai.OpenAIModel(openai.OpenAI(), model="...", max_tokens=64_000)
agent = Agent(model, extensions=extensions.load(MANIFEST))
```

Re-export your module from `infra/providers/__init__.py` guarded by `try`/`except ImportError` so other providers stay usable without it installed:

```python
try:
    from inloop.infra.providers import openai
except ImportError:
    pass
```