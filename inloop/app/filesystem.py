"""Port for reading and writing files on the local system."""

from typing import Protocol


class FileSystem(Protocol):
    """Reads and writes files on the local system."""

    def read_text(self, path: str) -> str:
        """Return the full text content of the file at the given path."""
        ...

    def write_text(self, path: str, content: str):
        """Write content to the file at the given path, replacing any existing content."""
        ...
