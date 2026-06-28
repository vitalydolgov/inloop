"""A named bundle of tools that can be added to the agent."""

import copy
from dataclasses import dataclass

from domain import tool


@dataclass
class Extension:
    """A named collection of tools contributed by a separate project."""

    name: str
    tools: list[tool.Tool]

    def qualified_name(self, t: tool.Tool) -> str:
        """Return the namespaced tool name: extension__tool."""
        return f"{self.name}__{t.name}"

    def tools_by_name(self) -> dict[str, tool.Tool]:
        """Return the extension's tools indexed by their namespaced name (extension__tool)."""
        return {
            self.qualified_name(t): copy.replace(t, name=self.qualified_name(t))
            for t in self.tools
        }
