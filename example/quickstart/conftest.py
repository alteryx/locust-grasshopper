"""A local API fixture for the performance suite quickstart."""

import json
from collections.abc import Iterator
from wsgiref.types import StartResponse, WSGIEnvironment

import gevent
import pytest
from gevent.pywsgi import WSGIServer


def application(environ: WSGIEnvironment, start_response: StartResponse) -> list[bytes]:
    """Serve two small JSON endpoints with simulated application work."""
    catalog = {
        "/products": {"items": [{"id": 1, "name": "Coffee mug"}]},
        "/categories": {"items": ["Home", "Office"]},
    }
    payload = catalog.get(environ["PATH_INFO"])
    status = "200 OK" if payload is not None else "404 Not Found"
    gevent.sleep(0.01)
    body = json.dumps(payload or {"error": "Not found"}).encode()
    start_response(
        status,
        [("Content-Type", "application/json"), ("Content-Length", str(len(body)))],
    )
    return [body]


@pytest.fixture(scope="session")
def local_api() -> Iterator[str]:
    """Keep the demo server available for the suite, then stop it."""
    server = WSGIServer(("127.0.0.1", 0), application, log=None)
    server.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.stop()
