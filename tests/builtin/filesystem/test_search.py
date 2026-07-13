"""Tests for the built-in filesystem search tool."""

import asyncio

from inloop.app.builtin.filesystem import search


class _FakeFileSystem:
    """A FileSystem serving text from an in-memory mapping of path to content."""

    def __init__(self, files: dict[str, str]) -> None:
        self._files = files

    def read_text(self, path: str) -> str:
        if path not in self._files:
            raise FileNotFoundError(f"No such file: {path}")
        return self._files[path]


def _search(files: dict[str, str], args: dict[str, object]) -> str:
    tool = search.search_tool(_FakeFileSystem(files))
    return asyncio.run(tool.execute(args))


def test_returns_matching_lines_with_line_numbers() -> None:
    out = _search(
        {"a.txt": "first\nneedle here\nlast needle"},
        {"path": "a.txt", "pattern": "needle"},
    )

    assert out == "2: needle here\n3: last needle"


def test_supports_regular_expressions() -> None:
    out = _search(
        {"a.txt": "item 1\nitem 20\nother"},
        {"path": "a.txt", "pattern": r"item \d+"},
    )

    assert out == "1: item 1\n2: item 20"


def test_can_ignore_case() -> None:
    out = _search(
        {"a.txt": "Needle\nother"},
        {"path": "a.txt", "pattern": "needle", "ignore_case": True},
    )

    assert out == "1: Needle"


def test_reports_when_there_are_no_matches() -> None:
    out = _search({"a.txt": "hello"}, {"path": "a.txt", "pattern": "missing"})

    assert out == "No matches found"


def test_invalid_pattern_returns_an_error_message() -> None:
    out = _search({"a.txt": "hello"}, {"path": "a.txt", "pattern": "["})

    assert out.startswith("Error: invalid pattern:")


def test_empty_pattern_returns_an_error_message() -> None:
    out = _search({"a.txt": "hello"}, {"path": "a.txt", "pattern": ""})

    assert out == "Error: `pattern` must not be empty"


def test_missing_file_returns_an_error_message() -> None:
    out = _search({}, {"path": "gone.txt", "pattern": "hello"})

    assert out.startswith("Error: could not read gone.txt")


def test_tool_is_named_search() -> None:
    assert search.search_tool(_FakeFileSystem({})).name == "search"
