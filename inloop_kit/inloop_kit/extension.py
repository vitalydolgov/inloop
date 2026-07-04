"""A named bundle of tools that can be added to the agent."""

from dataclasses import dataclass, replace

from inloop_kit.tool import Tool


@dataclass
class Extension:
    """A named collection of tools contributed by a separate project."""

    name: str
    tools: list[Tool]

    def qualified_name(self, t: Tool) -> str:
        """Return the namespaced tool name: extension__tool."""
        return f"{self.name}__{t.name}"

    def tools_by_name(self) -> dict[str, Tool]:
        """Return the extension's tools indexed by their namespaced name (extension__tool)."""
        return {
            self.qualified_name(t): replace(t, name=self.qualified_name(t))
            for t in self.tools
        }
