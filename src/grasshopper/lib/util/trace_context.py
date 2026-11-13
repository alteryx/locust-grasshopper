"""Context shared by Locust request naming and trace instrumentation."""

from contextlib import contextmanager
from contextvars import ContextVar

_ACTIVE_REQUEST_NAME: ContextVar[str | None] = ContextVar(
    "grasshopper_active_request_name", default=None
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
