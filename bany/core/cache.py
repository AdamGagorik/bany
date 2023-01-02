"""
This module defines a decorator for caching the results of an API call.
"""
import functools
import itertools
import pathlib
import uuid
from collections.abc import Callable
from typing import Any

from diskcache import Cache


NS = uuid.UUID("2a49a9ba-15cf-40d2-ab95-87961687a04f")
CACHE = Cache(directory=str(pathlib.Path.cwd()))


@functools.lru_cache
def compute_cache_key(*args, **kwargs) -> str:
    """
    Returns:
        A unique key generated from the argumnets to a function.
    """
    return str(
        uuid.uuid5(
            NS,
            "-".join(
                itertools.chain(
                    map(str, args),
                    (f"{k}:{v}" for k, v in kwargs.items()),
                )
            ),
        )
    )


def cached(*keys: Callable[[Any], Any]) -> Callable:
    """
    A decorator for caching the results of an API call.

    Args:
        keys: Functions (taking an object instance) that are used to compute the cache key.

    Returns:
        The decorated method.
    """

    def wrapper(method: Callable) -> Callable:
        @functools.wraps(method)
        def wrapped(self, *args, **kwargs):
            key = compute_cache_key(
                method.__name__,
                *(f(self) for f in keys),
                *args,
                **kwargs,
            )
            if key in CACHE:
                return CACHE[key]
            else:
                result = method(self, *args, **kwargs)
                CACHE[key] = result
                return result

        return wrapped

    return wrapper
