"""Port for listing, reading, writing, and managing files on the local system."""

from __future__ import annotations

from typing import Protocol


class FileSystem(Protocol):
    """Lists, reads, writes, and manages files on the local system."""

    def list(self, path: str) -> list[str]:
        """Return the names of the entries in the directory at the given path."""
        ...

    def find(self, path: str, pattern: str) -> list[str]:
        """Return files below path whose names match the given glob pattern."""
        ...

    def make_dir(self, path: str, parents: bool):
        """Create the directory at the given path, optionally creating missing parents."""
        ...

    def read_text(self, path: str) -> str:
        """Return the full text content of the file at the given path."""
        ...

    def write_text(self, path: str, content: str):
        """Write content to the file at the given path, replacing existing content."""
        ...

    def append_text(self, path: str, content: str):
        """Append content to the file at the given path, creating it when needed."""
        ...

    def move(self, source: str, destination: str):
        """Move a file or directory from source to a new destination path."""
        ...

    def copy(self, source: str, destination: str, recursive: bool):
        """Copy a file or directory to a new destination path."""
        ...

    def delete(self, path: str, recursive: bool):
        """Delete a file or directory, recursively when requested."""
        ...
