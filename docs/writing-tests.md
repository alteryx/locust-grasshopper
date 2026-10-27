# Write a Python performance test suite with Locust and pytest

[Project overview and quickstart](../README.md) ·
[Configuration](configuration.md) · [Checks and reporting](checks-and-reporting.md)

Grasshopper runs Locust journeys from pytest tests. Use fixtures for setup and
test data, journeys for repeated user actions, and assertions for the results
your application must meet.

## Start with the public API demo

Run the [quickstart](../README.md#quickstart), then open its four files in `example/`:

| File | Responsibility |
| --- | --- |
| [test_example.py](../example/test_example.py) | Request httpbin's `/get` endpoint and assert the results. |
| [conftest.py](../example/conftest.py) | Set short workload defaults that CLI, environment, and YAML settings can override. |
| [pytest.ini](../example/pytest.ini) | Load Grasshopper and show results in the terminal. |
| [example_scenarios.YAML](../example/example_scenarios.YAML) | Define smoke and iteration-limited workloads for the same journey. |

In the test, `ExampleJourney` extends `BaseJourney`, a Locust `HttpUser` subclass.
Its `host` is `https://httpbin.org`, and its `@task` method repeatedly requests
`/get`. The journey's `defaults` declare a 2000 ms budget for the 95th percentile
of response times.

`Grasshopper.launch_test(ExampleJourney, **complete_configuration)` starts the
workload and returns a Locust environment containing the results. Always pass the
`complete_configuration` fixture; it includes the configured load shape.

For a workload with several journey classes, `launch_test` also accepts a list of
classes or a mapping such as `{BrowseJourney: 3, CheckoutJourney: 1}`. These weights
control the mix of virtual users, while Locust task weights control actions within
a journey.

## Configure pytest

The demo's `pytest.ini` loads Grasshopper before other pytest plugins. Keep this
setting when copying the demo, or add it to your existing suite:

```ini
[pytest]
addopts = -p locust_grasshopper
```

Keep any existing `addopts` alongside it. Grasshopper sets up gevent before other
plugins import HTTP clients, so you can run the suite with ordinary `pytest`.
If you cannot change the pytest configuration, use
`python -m gevent.monkey --module pytest` to initialize gevent before pytest starts.

## Point the suite at your application

Copy the four example files into your own test directory. Change
`ExampleJourney.host` to your application's base URL, such as
`https://api.test.example.com`. Locust prepends it to the path in `self.client.get`.

Adapt the endpoint, named check, threshold name, timing budget, and wait time to
your application. Add pytest fixtures for authentication or test data as needed.

For application-specific values supplied through configuration, see
[journey settings](configuration.md#journey-settings).

## Change the workload

After pointing the journey at your own test environment, use the same entry point
as the quickstart:

```shell
pytest --users=10 --spawn_rate=5 --runtime=10
```

This starts up to ten users at five users per second, for ten seconds **per test
case**. The journey's `wait_time` controls the pause between task iterations.
Choose realistic traffic and longer runs when evaluating application performance;
the short public API demo is a way to learn the workflow.

For reusable workload definitions, see [YAML scenarios](configuration.md#yaml-scenarios).

## Make the results useful in CI

The demo asserts five things after each workload:

1. No journey errors were recorded.
2. At least one request completed.
3. No HTTP requests failed.
4. The `request URL is echoed` check ran and had no failures.
5. The configured p95 timing threshold passed.

Keep explicit assertions when adapting it. Locust records task exceptions, and
Grasshopper reports thresholds; neither substitutes for the pytest assertions.
See [checks and timing thresholds](checks-and-reporting.md) for additional criteria.

To see the demo fail, change its threshold `limit` from `2000` to `1` ms and rerun
it. Restore the value afterward.

Produce a report your CI system can collect with pytest's built-in JUnit support:

```shell
pytest --junitxml=results.xml
```

Pytest exits nonzero when an assertion fails. The target API must be reachable
from the CI runner; public API availability and network latency affect the demo's results.
