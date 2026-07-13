"""Tests for the built-in filesystem mkdir tool."""

import asyncio

from inloop.app.builtin.filesystem import mkdir


class _FakeFileSystem:
    """A FileSystem recording directories created through it."""

    def __init__(self) -> None:
        self.created: list[tuple[str, bool]] = []

    def make_dir(self, path: str, parents: bool):
        self.created.append((path, parents))


class _FailingFileSystem:
    """A FileSystem that refuses to create directories."""

    def make_dir(self, path: str, parents: bool):
        raise FileExistsError(path)


def _mkdir(fs, args: dict[str, object]) -> str:
    return asyncio.run(mkdir.mkdir_tool(fs).execute(args))


def test_creates_a_directory_without_parents_by_default() -> None:
    fs = _FakeFileSystem()

    out = _mkdir(fs, {"path": "build"})

    assert fs.created == [("build", False)]
    assert out == "Created directory build"


def test_can_create_missing_parent_directories() -> None:
    fs = _FakeFileSystem()

    _mkdir(fs, {"path": "build/output", "parents": True})

    assert fs.created == [("build/output", True)]


def test_creation_failure_returns_an_error_message() -> None:
    out = _mkdir(_FailingFileSystem(), {"path": "build"})

    assert out.startswith("Error: could not create directory build")


def test_tool_is_named_mkdir() -> None:
    assert mkdir.mkdir_tool(_FakeFileSystem()).name == "mkdir"
