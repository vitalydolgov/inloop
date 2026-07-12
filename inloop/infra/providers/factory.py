"""Builds a language model for a named provider from its settings."""

import os

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
                context_window=settings["context_window"],
                effort=settings.get("effort"),
                thinking_budget=settings.get("thinking_budget"),
            )
        case "openai":
            import openai

            from inloop.infra.providers import openai as adapter

            api_key = settings.get("api_key")
            if api_key is None:
                env_name = settings.get("env_key")
                if env_name:
                    api_key = os.getenv(env_name)

            return adapter.OpenAIModel(
                client=openai.AsyncOpenAI(
                    api_key=api_key,
                    base_url=settings.get("base_url"),
                ),
                model=settings["model"],
                max_tokens=settings["max_tokens"],
                context_window=settings["context_window"],
            )
    raise ValueError(f"unknown model provider: {provider!r}")
