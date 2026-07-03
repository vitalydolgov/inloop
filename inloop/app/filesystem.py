"""Port for reading files from the local system."""

from typing import Protocol


class FileSystem(Protocol):
    """Reads files from the local system."""

    def read_text(self, path: str) -> str:
        """Return the full text content of the file at the given path."""
        ...
