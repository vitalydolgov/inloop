"""Builds a language model for a named provider from its settings."""

from inloop.domain import model


def create_model(provider: str, settings: dict) -> model.Model:
    """Build a model for the named provider from its settings."""
    match provider:
        case "anthropic":
            import anthropic

            from inloop.infra.providers import anthropic as adapter

            return adapter.AnthropicModel(
                client=anthropic.AsyncAnthropic(),
                model=settings["model"],
                max_tokens=settings["max_tokens"],
                effort=settings.get("effort"),
                thinking_budget=settings.get("thinking_budget"),
            )
        case "together":
            import together

            from inloop.infra.providers import together as adapter

            return adapter.TogetherModel(
                client=together.AsyncTogether(),
                model=settings["model"],
                max_tokens=settings["max_tokens"],
            )
    raise ValueError(f"unknown model provider: {provider!r}")
