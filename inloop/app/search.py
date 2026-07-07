"""Port for searching file contents across the local system."""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class Match:
    """A single line in a file whose text matched a search."""

    path: str
    line: int
    text: str


class Search(Protocol):
    """Searches file contents across the local system."""

    def search(self, pattern: str, path: str, glob: str | None = None) -> list[Match]:
        """Return the lines under path matching the pattern, limited to files whose name matches glob when given."""
        ...
