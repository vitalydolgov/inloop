"""Shared API for extensions."""

from inloop.contrib.program import program
from inloop.contrib.tool import tool
from inloop.domain.extension import Extension

__all__ = ["Extension", "program", "tool"]
