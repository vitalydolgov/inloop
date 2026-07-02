"""A capability the model may request to use."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass
class Tool:
    """A named capability the model can ask to invoke, described by its inputs."""

    name: str
    description: str
    parameters: dict[str, object]
    execute: Callable[[dict[str, object]], Awaitable[str]]
