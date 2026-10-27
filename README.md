# locust-grasshopper: performance testing with Locust and pytest

**Build a repeatable performance test suite for your application.**

Grasshopper is a Python load testing framework that extends
[Locust](https://locust.io/) with [pytest](https://docs.pytest.org/). It helps
performance testers and SDETs reuse fixtures, run API workloads, and check
response times and failures as part of their test suite.

## Why use Grasshopper?

Locust runs your virtual users and records request statistics. Grasshopper adds
the test-suite workflow around it:

- **Reusable setup:** pytest fixtures for application setup, authentication, and test data.
- **Repeatable workloads:** YAML scenarios, tags, load shapes, and weighted user journeys.
- **Pass/fail criteria:** response checks, custom timings, and timing thresholds you can assert in pytest.
- **Reporting:** console results, pytest's JUnit output for CI, and optional InfluxDB or Datadog metrics.

## Quickstart

Use Python 3.11+ on Linux, macOS, or WSL. Native Windows is not currently supported
by the test runner's signal-based shutdown. The compatibility checks cover
Locust 2.47.0 on Python 3.11–3.15, plus Locust 2.43.3 on Python 3.11.

This demo starts its own local API. Clone the repository and run it:

```shell
git clone https://github.com/alteryx/locust-grasshopper.git
cd locust-grasshopper
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
cd example/quickstart
pytest
```

The two tests each run three virtual users for three seconds. They require
successful responses and a p95 response time at or below 500 ms. You should see
the threshold results and a `2 passed` summary. The local API stops automatically.
No Docker, running application, or metrics service is needed.

To add Grasshopper to an existing project, install `locust-grasshopper` with pip.

**Next:** [adapt the demo to your application](https://github.com/alteryx/locust-grasshopper/blob/main/docs/writing-tests.md).

## Documentation

| Guide | What you will learn |
| --- | --- |
| [Write a performance test suite](https://github.com/alteryx/locust-grasshopper/blob/main/docs/writing-tests.md) | Reuse pytest fixtures, change the workload, and produce CI results. |
| [Configure load tests and YAML scenarios](https://github.com/alteryx/locust-grasshopper/blob/main/docs/configuration.md) | Set users and runtime, select scenarios, and pass configuration into journeys. |
| [Checks, timing thresholds, and reporting](https://github.com/alteryx/locust-grasshopper/blob/main/docs/checks-and-reporting.md) | Define success, measure workflows, and send metrics to InfluxDB or Datadog. |

## Will a failed performance requirement fail CI?

When your test asserts it. Grasshopper records checks and threshold results;
your pytest assertions decide whether the test passes. The
[quickstart test](https://github.com/alteryx/locust-grasshopper/blob/main/example/quickstart/test_performance.py)
demonstrates this, including checks for missing traffic and journey errors.

## Contributing

[Open an issue](https://github.com/alteryx/locust-grasshopper/issues) for bugs or
ideas, or send a pull request. From the repository root, install development
dependencies and run the checks relevant to your change:

```shell
python -m pip install -e '.[dev]'
pytest tests/unit
ruff check .
ruff format --check .
```

Licensed under [Apache 2.0](https://github.com/alteryx/locust-grasshopper/blob/main/LICENSE).
