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
                effort=settings.get("effort"),
                thinking_budget=settings.get("thinking_budget"),
            )
        case "openai":
            import openai

            from inloop.infra.providers import openai as adapter

            return adapter.OpenAIModel(
                client=openai.AsyncOpenAI(
                    api_key=settings.get("api_key"),
                    base_url=settings.get("base_url"),
                ),
                model=settings["model"],
                max_tokens=settings["max_tokens"],
            )
        case "together":
            import openai

            from inloop.infra.providers import openai as adapter

            return adapter.OpenAIModel(
                client=openai.AsyncOpenAI(
                    api_key=settings.get("api_key") or os.getenv("TOGETHER_API_KEY"),
                    base_url=settings.get("base_url", "https://api.together.xyz/v1"),
                ),
                model=settings["model"],
                max_tokens=settings["max_tokens"],
            )
        case "fireworks":
            import openai

            from inloop.infra.providers import openai as adapter

            return adapter.OpenAIModel(
                client=openai.AsyncOpenAI(
                    api_key=settings.get("api_key") or os.getenv("FIREWORKS_API_KEY"),
                    base_url=settings.get("base_url", "https://api.fireworks.ai/inference/v1"),
                ),
                model=settings["model"],
                max_tokens=settings["max_tokens"],
            )
    raise ValueError(f"unknown model provider: {provider!r}")
