"""Tests for the built-in grep tool."""

import asyncio
import re

from inloop.app.builtin import grep
from inloop.app.search import Match


class _FakeSearch:
    """A Search that returns canned matches and records the arguments it was called with."""

    def __init__(self, matches: list[Match]) -> None:
        self._matches = matches
        self.calls: list[tuple[str, str, str | None]] = []

    def search(self, pattern: str, path: str, glob: str | None = None) -> list[Match]:
        self.calls.append((pattern, path, glob))
        return list(self._matches)


class _RaisingSearch:
    """A Search that fails as if the path could not be searched."""

    def search(self, pattern: str, path: str, glob: str | None = None) -> list[Match]:
        raise FileNotFoundError(path)


def _grep(search, args: dict[str, object]) -> str:
    return asyncio.run(grep.grep_tool(search).execute(args))


def test_formats_matches_as_path_line_text() -> None:
    search = _FakeSearch([Match("a.py", 3, "import os"), Match("b.py", 7, "import os")])

    out = _grep(search, {"pattern": "import"})

    assert out == "a.py:3:import os\nb.py:7:import os"


def test_defaults_the_path_to_the_current_directory() -> None:
    search = _FakeSearch([])

    _grep(search, {"pattern": "x"})

    assert search.calls == [("x", ".", None)]


def test_passes_the_glob_through() -> None:
    search = _FakeSearch([])

    _grep(search, {"pattern": "x", "path": "src", "glob": "*.py"})

    assert search.calls == [("x", "src", "*.py")]


def test_reports_when_there_are_no_matches() -> None:
    out = _grep(_FakeSearch([]), {"pattern": "absent"})

    assert out == "No matches found"


def test_invalid_pattern_is_reported_without_searching() -> None:
    search = _FakeSearch([])

    out = _grep(search, {"pattern": "("})

    assert out.startswith("Error: invalid pattern")
    assert search.calls == []


def test_search_failure_returns_an_error_message() -> None:
    out = _grep(_RaisingSearch(), {"pattern": "x", "path": "gone"})

    assert out.startswith("Error: could not search gone")


def test_caps_the_number_of_reported_matches() -> None:
    matches = [Match("f.py", n, "hit") for n in range(1, grep.MATCH_LIMIT + 6)]
    search = _FakeSearch(matches)

    out = _grep(search, {"pattern": "hit"})
    lines = out.splitlines()

    assert len(lines) == grep.MATCH_LIMIT + 1
    assert lines[-1] == "... (5 more matches)"


def test_tool_is_named_grep() -> None:
    assert grep.grep_tool(_FakeSearch([])).name == "grep"


def test_matches_a_real_regex_end_to_end() -> None:
    # The tool compiles the pattern itself; a valid regex must reach the search port.
    search = _FakeSearch([Match("a.py", 1, "value = 42")])

    out = _grep(search, {"pattern": r"\d+"})

    assert out == "a.py:1:value = 42"
    assert re.compile(search.calls[0][0])
