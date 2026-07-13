"""Tests for the built-in filesystem move tool."""

import asyncio

from inloop.app.builtin.filesystem import move


class _FakeFileSystem:
    """A FileSystem recording paths moved through it."""

    def __init__(self) -> None:
        self.moves: list[tuple[str, str]] = []

    def move(self, source: str, destination: str):
        self.moves.append((source, destination))


class _FailingFileSystem:
    """A FileSystem that refuses to move paths."""

    def move(self, source: str, destination: str):
        raise FileExistsError(destination)


def _move(fs, args: dict[str, object]) -> str:
    return asyncio.run(move.move_tool(fs).execute(args))


def test_moves_a_path_to_a_new_destination() -> None:
    fs = _FakeFileSystem()

    out = _move(fs, {"source": "old.txt", "destination": "new.txt"})

    assert fs.moves == [("old.txt", "new.txt")]
    assert out == "Moved old.txt to new.txt"


def test_move_failure_returns_an_error_message() -> None:
    out = _move(
        _FailingFileSystem(),
        {"source": "old.txt", "destination": "new.txt"},
    )

    assert out.startswith("Error: could not move old.txt to new.txt")


def test_tool_is_named_move() -> None:
    assert move.move_tool(_FakeFileSystem()).name == "move"
