"""Reads files from the local disk."""

from pathlib import Path


class LocalFileSystem:
    """A FileSystem backed by the local disk."""

    def read_text(self, path: str) -> str:
        """Return the full text content of the file at the given path."""
        return Path(path).read_text()
