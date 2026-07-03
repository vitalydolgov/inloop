"""A capability the model may request to use."""

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import wraps


@dataclass
class Tool:
    """A named capability the model can ask to invoke, described by its inputs."""

    name: str
    description: str
    parameters: dict[str, object]
    execute: Callable[[dict[str, object]], Awaitable[str]]


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
