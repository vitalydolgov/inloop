"""Safe wrapper decorator for tool executors."""

import inspect
from collections.abc import Callable
from functools import wraps


def rescue(fn: Callable) -> Callable:
    """Catch exceptions and return them as strings.

    If the wrapped function is annotated '-> None', returns 'ok' on success.
    """
    is_proc = inspect.signature(fn).return_annotation is None
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            result = fn(*args, **kwargs)
            return "ok" if is_proc else result
        except Exception as exc:
            return str(exc)
    return wrapper
