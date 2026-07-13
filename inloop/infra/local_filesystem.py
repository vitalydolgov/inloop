"""Lists directories, reads and writes files, and manages paths on the local disk."""

from __future__ import annotations

import shutil
from pathlib import Path


class LocalFileSystem:
    """A FileSystem backed by the local disk."""

    def list(self, path: str) -> list[str]:
        """Return the names of the entries in the directory at the given path."""
        entries = []
        for entry in Path(path).iterdir():
            entries.append(entry.name)
        return entries

    def find(self, path: str, pattern: str) -> list[str]:
        """Return files below path whose names match the given glob pattern."""
        root = Path(path)
        if not root.exists():
            raise FileNotFoundError(path)
        if not root.is_dir():
            raise NotADirectoryError(path)
        matches = []
        for entry in root.rglob(pattern):
            if entry.is_file():
                matches.append(str(entry))
        return matches

    def make_dir(self, path: str, parents: bool):
        """Create the directory at the given path, optionally creating missing parents."""
        Path(path).mkdir(parents=parents)

    def read_text(self, path: str) -> str:
        """Return the full text content of the file at the given path."""
        return Path(path).read_text()

    def write_text(self, path: str, content: str):
        """Write content to the file at the given path, replacing existing content."""
        Path(path).write_text(content)

    def append_text(self, path: str, content: str):
        """Append content to the file at the given path, creating it when needed."""
        with Path(path).open("a") as file:
            file.write(content)

    def move(self, source: str, destination: str):
        """Move a file or directory from source to a new destination path."""
        target = Path(destination)
        if target.exists():
            raise FileExistsError(destination)
        Path(source).rename(target)

    def copy(self, source: str, destination: str, recursive: bool):
        """Copy a file or directory to a new destination path."""
        source_path = Path(source)
        target = Path(destination)
        if target.exists():
            raise FileExistsError(destination)
        if source_path.is_dir() and not source_path.is_symlink():
            if not recursive:
                raise IsADirectoryError(source)
            shutil.copytree(source_path, target)
            return
        shutil.copy2(source_path, target)

    def delete(self, path: str, recursive: bool):
        """Delete a file or directory, recursively when requested."""
        target = Path(path)
        if target.is_dir() and not target.is_symlink():
            if recursive:
                shutil.rmtree(target)
            else:
                target.rmdir()
            return
        target.unlink()
