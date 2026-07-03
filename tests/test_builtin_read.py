"""Tests for the built-in read tool."""

import asyncio

from inloop.app.builtin import read


class _FakeFileSystem:
    """A FileSystem serving text from an in-memory mapping of path to content."""

    def __init__(self, files: dict[str, str]) -> None:
        self._files = files

    def read_text(self, path: str) -> str:
        if path not in self._files:
            raise FileNotFoundError(f"No such file: {path}")
        return self._files[path]


def _read(files: dict[str, str], args: dict[str, object]) -> str:
    tool = read.read_tool(_FakeFileSystem(files))
    return asyncio.run(tool.execute(args))


def test_reads_whole_file_as_numbered_lines() -> None:
    out = _read({"a.txt": "hello\nworld"}, {"path": "a.txt"})

    assert out == "     1\thello\n     2\tworld"


def test_offset_skips_leading_lines_but_keeps_numbering() -> None:
    out = _read({"a.txt": "one\ntwo\nthree"}, {"path": "a.txt", "offset": 2})

    assert out == "     2\ttwo\n     3\tthree"


def test_limit_caps_the_number_of_lines() -> None:
    out = _read({"a.txt": "one\ntwo\nthree"}, {"path": "a.txt", "limit": 2})

    assert out == "     1\tone\n     2\ttwo"


def test_offset_and_limit_select_a_window() -> None:
    out = _read({"a.txt": "one\ntwo\nthree\nfour"}, {"path": "a.txt", "offset": 2, "limit": 2})

    assert out == "     2\ttwo\n     3\tthree"


def test_missing_file_returns_an_error_message() -> None:
    out = _read({}, {"path": "gone.txt"})

    assert out.startswith("Error: could not read gone.txt")


def test_empty_file_reports_it_is_empty() -> None:
    out = _read({"a.txt": ""}, {"path": "a.txt"})

    assert out == "a.txt is empty"


def test_offset_past_the_end_reports_an_empty_range() -> None:
    out = _read({"a.txt": "one\ntwo"}, {"path": "a.txt", "offset": 5})

    assert out == "a.txt has no lines in the requested range"


def test_tool_is_named_read() -> None:
    tool = read.read_tool(_FakeFileSystem({}))

    assert tool.name == "read"
