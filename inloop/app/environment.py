"""Port for the ambient facts the agent shares with the model."""

from typing import Protocol


class Environment(Protocol):
    """Describes the world the agent runs in, for the model's system prompt."""

    def describe(self) -> str:
        """Return a description of the current environment."""
        ...
