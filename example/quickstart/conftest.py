"""A local API fixture for the performance suite quickstart."""

import json
from collections.abc import Iterator
from wsgiref.types import StartResponse, WSGIEnvironment

import gevent
import pytest
from gevent.pywsgi import WSGIServer


def application(environ: WSGIEnvironment, start_response: StartResponse) -> list[bytes]:
    """Serve a product catalog with simulated application work."""
    if environ["PATH_INFO"] == "/products":
        status = "200 OK"
        payload = {"items": [{"id": 1, "name": "Coffee mug"}]}
    else:
        status = "404 Not Found"
        payload = {"error": "Not found"}
    gevent.sleep(0.01)
    body = json.dumps(payload).encode()
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
