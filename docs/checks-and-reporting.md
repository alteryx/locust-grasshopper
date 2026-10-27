# Performance checks, timing thresholds, and metrics reporting

[Project overview](../README.md) · [Writing tests](writing-tests.md) ·
[Configuration](configuration.md)

Grasshopper adds named checks and timing thresholds to Locust statistics. Use
pytest assertions on the results to enforce your application's requirements.
InfluxDB and Datadog are optional; local console reporting works without either.

Console reports use Rich tables with green PASS, yellow WARN, and red FAIL labels.
Colors are automatic in a terminal. If your IDE or CI captures output, use
`FORCE_COLOR=1 pytest` to enable them, or `NO_COLOR=1 pytest` to turn colors off.

## Timing thresholds

The [quickstart](../example/test_example.py) declares thresholds in
`ExampleJourney.defaults`. This sets a 2000 ms budget for the 95th percentile of
`GET /get` response times:

```python
defaults = {
    "thresholds": {
        "/get": {"type": "GET", "percentile": 0.95, "limit": 2000},
    },
}
```

The key must match the Locust request's name. It defaults to the request path;
when you supply `name="product lookup"` to `self.client.get`, use that name instead.
`limit` is in milliseconds and `percentile` is a fraction; its default is `0.9`.

After `launch_test` returns, inspect and assert the result:

```python
threshold = environment.stats.trends["/get"]["thresholds"][0]
assert threshold["succeeded"], threshold
```

Also assert that requests completed and that errors are acceptable, as the demo
does. To define budgets in YAML, put the threshold dictionary under
`grasshopper_scenario_args.thresholds` and
[pass the configuration to the journey](configuration.md#journey-settings).
These settings override the journey's defaults.

## Response and workflow checks

Call `check` inside a journey to record a named pass/fail result. The quickstart
uses this check to verify that httpbin echoes the requested URL:

```python
from grasshopper.lib.util.utils import check

response = self.client.get("/get")
check(
    "request URL is echoed",
    response.status_code == 200 and response.json().get("url") == response.url,
    env=self.environment,
    tags={"journey": "example"},
)
```

Checks are aggregated by name. After the workload, enforce the result in pytest:

```python
result = environment.stats.checks["request URL is echoed"]
assert result["total"] > 0
assert result["failed"] == 0, result
```

`halt_on_failure=True` stops the runner after a failed check. Keep the pytest
assertions so an early stop also produces a failing test.

## Time a multi-request workflow

Add a `custom_trend` decorator to a journey method to measure its total duration.
For an application with `/products` and `/categories` endpoints, add this task to
your journey, with the imports at module level. Adapt the paths to your application.

```python
from grasshopper.lib.util.utils import custom_trend
from locust import task


@task
@custom_trend("browse catalog")
def browse_catalog(self):
    self.client.get("/products")
    self.client.get("/categories")
```

To add a threshold for this timing, use the name `browse catalog` and type `CUSTOM`.

## InfluxDB and Grafana

Set `--influx_host` to enable InfluxDB reporting. Related options include
`--influx_port`, `--influx_user`, `--influx_pwd`, `--influx_ssl`, and
`--influx_verify_ssl`. `--grafana_host` controls generated Grafana links.

For local exploration, the repository includes an
[InfluxDB/Grafana Compose example](../example/observability_infrastructure/docker-compose.yml).
From the repository root:

```shell
docker compose -f example/observability_infrastructure/docker-compose.yml up -d
```

Grafana is available at `http://localhost:3000` with initial credentials
`admin` / `admin`. From your test directory, run with
`pytest --influx_host=localhost`.

Request `context` values become extra InfluxDB tags, for example:

```python
self.client.get("/products", name="product lookup", context={"journey": "catalog"})
```

## Datadog

Set both `DD_API_KEY` and `DD_ENV` to enable Datadog reporting. `DD_SITE` defaults
to `datadoghq.com`; `DD_SERVICE` and `DD_VERSION` add service and version tags.
Metric submission is buffered outside the request path.

Metrics use the `grasshopper.` prefix by default:

- `locust_requests.count`, `locust_requests.response_time`, `locust_requests.response_length`, and `locust_requests.error`.
- `locust_checks.total`, `locust_checks.passed`, and `locust_checks.failed`.
- Numeric custom fields as `<measurement>.<field>`.

For example, the request count metric is `grasshopper.locust_requests.count`.
Request metrics include name, request type, environment, and status-code tags;
arbitrary request `context` values are not forwarded as Datadog request tags.
Checks and custom metric points accept their own extra tags.

If both backends are configured, Grasshopper reports to both. Contributor-facing
background is in the [listener design diagram](database_listener_design_documentation.md).
