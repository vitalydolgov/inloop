"""A multi-turn conversation transcript."""

from domain.message import Role, Message


class Conversation:
    """An ongoing exchange that remembers prior turns."""

    def __init__(self) -> None:
        self.history: list[Message] = []
        """The messages exchanged so far, in order."""

    def add(self, role: Role, content: str) -> None:
        """Append a message to the transcript."""
        self.history.append(Message(role, content))
