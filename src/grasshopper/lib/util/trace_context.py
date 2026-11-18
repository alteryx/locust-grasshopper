"""Context shared by Locust request naming and trace instrumentation."""

from contextlib import contextmanager
from contextvars import ContextVar

_ACTIVE_REQUEST_NAME: ContextVar[str | None] = ContextVar(
    "grasshopper_active_request_name", default=None
)
_ACTIVE_TREND_NAME: ContextVar[str | None] = ContextVar(
    "grasshopper_active_trend_name", default=None
)


@contextmanager
def request_name(name: str | None):
    """Expose the current Locust request name while the HTTP request executes."""
    token = _ACTIVE_REQUEST_NAME.set(name)
    try:
        yield
    finally:
        _ACTIVE_REQUEST_NAME.reset(token)


def active_request_name() -> str | None:
    """Return the Locust request name for the current execution context."""
    return _ACTIVE_REQUEST_NAME.get()


@contextmanager
def trend_name(name: str | None):
    """Expose the current custom trend while its journey function executes."""
    token = _ACTIVE_TREND_NAME.set(name)
    try:
        yield
    finally:
        _ACTIVE_TREND_NAME.reset(token)


def active_trend_name() -> str | None:
    """Return the custom trend for the current execution context."""
    return _ACTIVE_TREND_NAME.get()
