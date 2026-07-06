"""Port providing the model a role runs on."""

from typing import Protocol

from inloop.domain import model


class ModelConfig(Protocol):
    """Provides the model a role runs on, if one is configured for it."""

    def model(self) -> model.Model | None:
        """Return the configured model, or None when none is declared."""
        ...
