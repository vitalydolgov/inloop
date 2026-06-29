"""Discovers and loads extensions registered under the inloop.extensions entry point."""

from importlib.metadata import entry_points

from domain import extension

GROUP = "inloop.extensions"


def load() -> list[extension.Extension]:
    """Load every installed extension registered in the inloop.extensions group."""
    return [ep.load() for ep in entry_points(group=GROUP)]
