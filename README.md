# locust-grasshopper: performance testing with Locust and pytest

**Build a repeatable performance test suite for your application.**

Grasshopper is an open source Python performance testing framework that combines
[Locust](https://locust.io/) load generation with [pytest](https://docs.pytest.org/)
fixtures, assertions, and test execution. It adds configurable latency thresholds,
named checks, workflow timing, and InfluxDB and Datadog metrics reporting for
repeatable API load tests.

## Why use Grasshopper?

Locust runs your virtual users and records request statistics. Grasshopper adds
the test-suite workflow around it:

- **[pytest load testing](https://github.com/alteryx/locust-grasshopper/blob/main/docs/writing-tests.md):**
  reuse fixtures for setup, authentication, and test data; assert results and produce JUnit reports for CI.
- **[Repeatable API workloads](https://github.com/alteryx/locust-grasshopper/blob/main/docs/configuration.md):**
  configure YAML scenarios, tags, load shapes, and weighted Locust journeys.
- **[Latency thresholds](https://github.com/alteryx/locust-grasshopper/blob/main/docs/checks-and-reporting.md#timing-thresholds) and [checks](https://github.com/alteryx/locust-grasshopper/blob/main/docs/checks-and-reporting.md#response-and-workflow-checks):**
  set response-time budgets and assert pass/fail results in pytest.
- **[Workflow timing](https://github.com/alteryx/locust-grasshopper/blob/main/docs/checks-and-reporting.md#time-a-multi-request-workflow):**
  measure latency across multiple API requests using custom trends.
- **Metrics reporting:** view console results or send metrics to
  [InfluxDB](https://github.com/alteryx/locust-grasshopper/blob/main/docs/checks-and-reporting.md#influxdb-and-grafana) and
  [Datadog](https://github.com/alteryx/locust-grasshopper/blob/main/docs/checks-and-reporting.md#datadog).

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

The test runs three virtual users for three seconds. It requires successful
responses and a p95 response time at or below 500 ms. You should see the threshold
results and a `1 passed` summary. The local API stops automatically.
No Docker, running application, or metrics service is needed.

To add Grasshopper to an existing project, run
`python -m pip install locust-grasshopper` and
[configure pytest](https://github.com/alteryx/locust-grasshopper/blob/main/docs/writing-tests.md#configure-pytest).
Published versions are listed on [PyPI](https://pypi.org/project/locust-grasshopper/#history).

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
