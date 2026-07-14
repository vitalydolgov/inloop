"""Agent instructions read from an AGENTS.md file."""

from pathlib import Path


class AgentsFile:
    """An Instructions adapter backed by a Markdown file."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> str:
        """Return the file contents, or no instructions when it is absent."""
        if not self._path.exists():
            return ""
        return self._path.read_text()
