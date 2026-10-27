"""Module: Decorators."""

import functools
import logging
from collections.abc import Callable
from typing import Generic, TypeVar

logger = logging.getLogger()

T = TypeVar("T")


class classproperty(Generic[T]):
    """Evaluate a property on its accessing class, including subclasses."""

    def __init__(self, getter: Callable[[type], T]) -> None:
        self.getter = getter

    def __get__(self, instance: object, owner: type | None = None) -> T:
        return self.getter(owner if owner is not None else type(instance))


def deprecate(deprecated, redirect):
    """Log a deprecation message at the warning level before method execution.

    We didn't add the [deprecation](https://pypi.org/project/deprecation/) package
    because we only needed this one decorator right now. If we end up wanting to
    add any additional functionality along these lines, we should add this package.
    """

    def decorator_deprecate(func):
        @functools.wraps(func)
        def wrapper_deprecate(*args, **kwargs):
            logger.warning(
                f"Method '{deprecated}' is deprecated, please use '{redirect}' instead."
            )
            value = func(*args, **kwargs)
            return value

        return wrapper_deprecate

    return decorator_deprecate
