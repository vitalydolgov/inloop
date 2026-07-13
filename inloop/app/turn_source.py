"""The live tools and model stream a turn uses."""

from collections.abc import AsyncIterator

from inloop.app.conversation import Conversation
from inloop.app.server_tools import ServerTools
from inloop.domain import extension
from inloop.domain import model
from inloop.domain import streaming
from inloop.domain import tool


class TurnSource:
    """Opening context for a turn: tools available now and a model stream."""

    def __init__(
        self,
        model: model.Model,
        *,
        extensions: list[extension.Extension] | None = None,
        server_tools: ServerTools | None = None,
        extra_tools: list[tool.Tool] | None = None,
    ):
        self._model = model
        self._extensions = list(extensions or [])
        self._server_tools = server_tools
        self._extra_tools = list(extra_tools or [])

    def tools(self) -> dict[str, tool.Tool]:
        """Return the tools available right now, keyed by name."""
        tools: dict[str, tool.Tool] = {}
        for ext in self._extensions:
            tools.update(ext.tools_by_name())
        if self._server_tools:
            for t in self._server_tools.tools():
                tools[t.name] = t
        for t in self._extra_tools:
            tools[t.name] = t
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
