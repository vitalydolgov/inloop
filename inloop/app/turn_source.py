"""The live tools and model stream a turn uses."""

from collections.abc import AsyncIterator

from inloop.app.conversation import Conversation
from inloop.app.server_tools import ServerTools
from inloop.app.spawn import Spawner, TOOL_NAME as SPAWN_TOOL
from inloop.domain import extension
from inloop.domain import model
from inloop.domain import streaming
from inloop.domain import tool


class TurnSource:
    """Opening context for a turn: tools available now and a model stream."""

    def __init__(
        self,
        model: model.Model,
        extensions: list[extension.Extension] = [],
        server_tools: ServerTools | None = None,
        spawner: Spawner | None = None,
    ):
        self._model = model
        self._extensions = extensions
        self._server_tools = server_tools
        self._spawner = spawner

    def tools(self) -> dict[str, tool.Tool]:
        """Return the tools available right now, keyed by name."""
        tools: dict[str, tool.Tool] = {}
        for ext in self._extensions:
            tools.update(ext.tools_by_name())
        if self._server_tools:
            for t in self._server_tools.tools():
                tools[t.name] = t
        if self._spawner:
            tools[SPAWN_TOOL] = self._spawner.tool()
        return tools

    def stream(
        self,
        conversation: Conversation,
        system_prompt: str = "",
    ) -> AsyncIterator[streaming.Event]:
        """Open a model stream for the conversation with the tools available now."""
        return self._model.stream(
            conversation.history,
            list(self.tools().values()),
            system=system_prompt,
        )
