"""Port for installing, removing, listing, and loading extensions."""

from pathlib import Path
from typing import Protocol

from inloop.domain import extension


class ExtensionRegistry(Protocol):
    """Installs, removes, lists, and loads extensions."""

    def install(self, source: str) -> str:
        """Install an extension from a path or git url and return its name."""
        ...

    def uninstall(self, name: str) -> None:
        """Remove an installed extension."""
        ...

    def installed(self) -> dict[str, str]:
        """Return installed extension names mapped to the source they were installed from."""
        ...

    def paths(self) -> list[Path]:
        """Return the directory of every installed extension."""
        ...

    def load(self) -> list[extension.Extension]:
        """Load every installed extension."""
        ...
