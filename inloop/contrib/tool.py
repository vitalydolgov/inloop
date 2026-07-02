"""Decorators for implementing extension tools."""

import asyncio
import inspect
from collections.abc import Callable
from functools import wraps

from inloop.domain.tool import Tool


def _transform(fn: Callable) -> Callable:
    is_proc = inspect.signature(fn).return_annotation is None
    is_async = inspect.iscoroutinefunction(fn)
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        if is_async:
            result = await fn(*args, **kwargs)
        else:
            result = await asyncio.to_thread(fn, *args, **kwargs)
        return "ok" if is_proc else result
    return wrapper


def tool(
    name: str,
    description: str,
    parameters: dict[str, object],
) -> Callable[[Callable], Tool]:
    """Decorator that wraps a function as a Tool."""
    def decorator(fn: Callable) -> Tool:
        return Tool(name=name, description=description, parameters=parameters, execute=_transform(fn))
    return decorator
