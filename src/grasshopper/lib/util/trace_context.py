"""Context shared by Grasshopper custom trend instrumentation."""

from contextlib import contextmanager
from contextvars import ContextVar

_ACTIVE_TREND_NAME: ContextVar[str | None] = ContextVar(
    "grasshopper_active_trend_name", default=None
)


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
