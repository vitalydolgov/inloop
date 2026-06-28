"""Workflow for a single user request."""

from collections.abc import Iterator

from domain import model
from domain import streaming


def ask(language_model: model.Model, message: str) -> Iterator[streaming.StreamEvent]:
    """Stream the model's response to a single user message."""
    yield from language_model.stream(message)
