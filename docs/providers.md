# Providers

A provider is an adapter between the agent and a specific LLM backend. Below are the built-in providers and instructions for writing a new one.

## Built-in providers

Each provider lives in its own module under `infra/providers/` and is re-exported from `infra/providers/__init__.py`.

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
    effort="low"
)
```

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

**Wire it in.** Construct your provider and hand it to the `Agent`:

```python
import openai
from inloop.infra import providers

model = providers.openai.OpenAIModel(openai.OpenAI(), model="...", max_tokens=64_000)
agent = Agent(model, extensions=extensions.load(MANIFEST))
```

Pass `subagent_model` to run spawned subagents on a different `Model` than the parent — e.g. a lower effort setting for the cheaper, more scoped work a subagent does.

Re-export your module from `infra/providers/__init__.py` guarded by `try`/`except ImportError` so other providers stay usable without it installed:

```python
try:
    from inloop.infra.providers import openai
except ImportError:
    pass
```