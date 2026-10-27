# Write a Python performance test suite with Locust and pytest

[Project overview and quickstart](../README.md) ·
[Configuration](configuration.md) · [Checks and reporting](checks-and-reporting.md)

Grasshopper runs Locust journeys from pytest tests. Use fixtures for setup and
test data, journeys for repeated user actions, and assertions for the results
your application must meet.

## Start with the local API demo

Run the [quickstart](../README.md#quickstart), then open its three files:

| File | Responsibility |
| --- | --- |
| [conftest.py](../example/quickstart/conftest.py) | Start a local API on an available loopback port and stop it after the suite. |
| [test_performance.py](../example/quickstart/test_performance.py) | Run the same journey against two endpoints and assert the results. |
| [pytest.ini](../example/quickstart/pytest.ini) | Set a short workload and show results in the terminal. |

In the test, `CatalogJourney` extends `BaseJourney`, a Locust `HttpUser` subclass.
Its `@task` method repeatedly requests the selected endpoint. Pytest parametrization
runs `/products` and `/categories` as separate test cases.

`Grasshopper.launch_test(CatalogJourney, **complete_configuration)` starts the
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

Copy the three quickstart files into your own test directory. Replace the demo
`conftest.py` with a fixture that supplies your application's base URL:

```python
import os

import pytest


@pytest.fixture(scope="session")
def local_api() -> str:
    return os.environ["APP_BASE_URL"]
```

Set `APP_BASE_URL` to your test environment before running pytest. The fixture
keeps the name used by the demo; you can rename it together with the test argument.
Adapt the endpoint list, expected response body, timing budget, and wait time to
your application. Add fixtures for authentication or test data as needed.

Pass fixture values into the journey through the dictionary already supplied to
`CatalogJourney.replace_incoming_scenario_args(...)`. For example, add a
`"tenant_id": tenant_id` entry and read it in a task with
`self.scenario_args["tenant_id"]`. Journey `defaults` provide fallback values;
incoming scenario arguments take precedence.

## Change the workload

From your test directory, use the same entry point as the quickstart:

```shell
pytest --users=10 --spawn_rate=5 --runtime=10
```

This starts up to ten users at five users per second, for ten seconds **per test
case**. The journey's `wait_time` controls the pause between task iterations.
Choose realistic traffic and longer runs when evaluating application performance;
the short local demo is a way to learn the workflow.

For reusable workload definitions, see [YAML scenarios](configuration.md#yaml-scenarios).

## Make the results useful in CI

The demo asserts four things after each workload:

1. No journey errors were recorded.
2. At least one request completed.
3. No requests failed, including the response-body validation in the journey.
4. The configured p95 timing threshold passed.

Keep explicit assertions when adapting it. Locust records task exceptions, and
Grasshopper reports thresholds; neither substitutes for the pytest assertions.
See [checks and timing thresholds](checks-and-reporting.md) for additional criteria.

To see the demo fail, change its threshold `limit` from `500` to `1` ms and rerun
it. Restore the value afterward.

Produce a report your CI system can collect with pytest's built-in JUnit support:

```shell
pytest --junitxml=results.xml
```

Pytest exits nonzero when an assertion fails. Your application must be available
to the CI runner; the quickstart's fixture supplies the server only for the demo.
