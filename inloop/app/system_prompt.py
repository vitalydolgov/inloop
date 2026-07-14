"""Assembles the system prompt supplied to an agent."""

from inloop.app.instructions import Instructions
from inloop.app.environment import Environment


def compose(environment: Environment, instructions: Instructions) -> str:
    """Combine environment facts and configured agent instructions."""
    parts = []
    for text in [environment.describe(), instructions.load()]:
        if text:
            parts.append(text)
    return "\n\n".join(parts)
