"""Port for instructions supplied to the agent at startup."""

from typing import Protocol


class Instructions(Protocol):
    """Provides instructions that become part of the agent's system prompt."""

    def load(self) -> str:
        """Return the instructions for the agent."""
        ...
