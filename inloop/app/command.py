"""An instruction aimed at the harness rather than the model, typed as /name."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass
class Command:
    """A named action the user asks the harness to perform."""

    name: str
    description: str
    run: Callable[[], Awaitable[None]]
