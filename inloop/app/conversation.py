"""A multi-turn conversation transcript."""

from inloop.domain.message import Message


class Conversation:
    """An ongoing exchange that remembers prior turns."""

    def __init__(self) -> None:
        self.history: list[Message] = []
        """The messages exchanged so far, in order."""

    def add(self, message: Message) -> None:
        """Append a message to the transcript."""
        self.history.append(message)
