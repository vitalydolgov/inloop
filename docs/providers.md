# Providers

Supported LLM backends and how to configure them.

## Anthropic

```sh
uv sync --extra anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
```

```python
import anthropic
from infra.anthropic_model import AnthropicModel

model = AnthropicModel(anthropic.Anthropic(), model="claude-haiku-4-5")
```

## Together AI

```sh
uv sync --extra together
export TOGETHER_API_KEY="..."
```

```python
import together
from infra.together_model import TogetherModel

model = TogetherModel(together.Together(), model="google/gemma-4-31B-it")
```

Both classes accept optional `model` and `max_tokens` keyword arguments to override the defaults.
