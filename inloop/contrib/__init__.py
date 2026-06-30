"""Shared API for extensions."""

from inloop.domain.extension import Extension
from inloop.domain.tool import Tool
from inloop.contrib.rescue import rescue

__all__ = ["Extension", "Tool", "rescue"]
