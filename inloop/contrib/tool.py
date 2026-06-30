"""Decorators for implementing extension tools."""

import inspect
from collections.abc import Callable
from functools import wraps

from inloop.domain.tool import Tool


def _rescue(fn: Callable) -> Callable:
    is_proc = inspect.signature(fn).return_annotation is None
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            result = fn(*args, **kwargs)
            return "ok" if is_proc else result
        except Exception as exc:
            return str(exc)
    return wrapper


def tool(
    name: str,
    description: str,
    parameters: dict[str, object],
) -> Callable[[Callable], Tool]:
    """Decorator that wraps a function as a Tool, catching exceptions as error strings."""
    def decorator(fn: Callable) -> Tool:
        return Tool(name=name, description=description, parameters=parameters, execute=_rescue(fn))
    return decorator
