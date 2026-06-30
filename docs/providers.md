# Providers

Supported LLM backends and how to configure them.

A provider is an adapter that lets the agent talk to a specific LLM backend. The agent depends only on the `domain.model.Model` port, so adding a backend never touches `domain` or `app` — see [Writing your own provider](#writing-your-own-provider).

## Built-in providers

### Anthropic

```sh
uv sync --extra anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
```

```python
import anthropic
from inloop.infra.anthropic_model import AnthropicModel

model = AnthropicModel(
    anthropic.Anthropic(),
    model="claude-sonnet-4-6",
    max_tokens=64_000,
    effort="high",
)
```

### Together AI

```sh
uv sync --extra together
export TOGETHER_API_KEY="..."
```

```python
import together
from inloop.infra.together_model import TogetherModel

model = TogetherModel(
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

It is a concrete adapter, so it lives in `infra/` (e.g. `infra/openai_model.py`) and may import the backend SDK freely. Implementing one is three translations:

**1. Domain messages → backend format.** Walk each `Message` and map its content blocks onto whatever shape the backend expects. `infra/together_model.py` shows this for an OpenAI-style chat API.

**2. Domain tools → backend specs.** Render each `Tool`'s `name`, `description`, and `parameters` (a JSON Schema) into the backend's function/tool format. Only send tools when the list is non-empty.

**3. Backend stream → `streaming.Event`s.** Consume the backend's streamed chunks and yield domain events in order:

- `ThinkingPhase.STARTED` / `ThinkingDelta` / `ThinkingPhase.ENDED` — wrap reasoning output, if the backend exposes it.
- `TextDelta` — each chunk of visible answer text.
- `ToolUse(id, name, input)` — one per requested tool call, with `input` decoded to a `dict` (accumulate streamed argument fragments first).
- `MessageCompleted(text, stop_reason)` — emit exactly once, last, with the full concatenated text and the backend's stop reason.

The agent loop reads only these events, so any backend you can stream from will work.

**Wire it in.** Construct your provider and hand it to the `Agent`:

```python
from infra.openai_model import OpenAIModel

model = OpenAIModel(client, model="...", max_tokens=64_000)
agent = Agent(model, extensions=extensions.load(MANIFEST))
```

If the backend needs an SDK that should not always be installed, add it as an optional dependency (an extra) in `pyproject.toml`.