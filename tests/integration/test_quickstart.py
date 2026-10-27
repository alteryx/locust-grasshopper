"""Exercise the published example without depending on the public demo API."""

from pathlib import Path

import pytest

pytest_plugins = ["pytester"]
EXAMPLE = Path(__file__).resolve().parents[2] / "example"


@pytest.mark.parametrize(
    "args,passed",
    [
        ([], True),
        (["example_scenarios.YAML", "--tags=smoke"], True),
        (["example_scenarios.YAML", "--tags=iterations"], True),
        ([], False),
    ],
)
def test_quickstart(pytester: pytest.Pytester, args: list[str], passed: bool) -> None:
    pytester.makeini((EXAMPLE / "pytest.ini").read_text())
    pytester.makepyfile(test_example=(EXAMPLE / "test_example.py").read_text())
    pytester.makefile(
        ".YAML", example_scenarios=(EXAMPLE / "example_scenarios.YAML").read_text()
    )
    pytester.makeconftest(
        (EXAMPLE / "conftest.py").read_text()
        + f"""

@pytest.fixture(autouse=True)
def use_test_api():
    import json
    import gevent
    from gevent.pywsgi import WSGIServer
    from test_example import ExampleJourney

    def application(environ, start_response):
        url = "http://" + environ["HTTP_HOST"] + environ["PATH_INFO"]
        if not {passed!r}:
            url = "https://wrong.example/get"
        gevent.sleep(0.01)
        body = json.dumps({{"url": url}}).encode()
        start_response(
            "200 OK",
            [("Content-Type", "application/json"), ("Content-Length", str(len(body)))],
        )
        return [body]

    server = WSGIServer(("127.0.0.1", 0), application, log=None)
    server.start()
    ExampleJourney.host = "http://127.0.0.1:" + str(server.server_port)
    try:
        yield
    finally:
        server.stop()
"""
    )

    result = pytester.runpytest_subprocess(*args, timeout=20)
    result.assert_outcomes(passed=int(passed), failed=int(not passed))
    assert "request URL is echoed" in result.stdout.str()
