# Configure Locust/pytest load tests and YAML scenarios

[Project overview](../README.md) · [Writing tests](writing-tests.md) ·
[Checks and reporting](checks-and-reporting.md)

Grasshopper merges workload and application settings into the
`complete_configuration` pytest fixture, a dictionary-like `GHConfiguration`.
Pass it to `Grasshopper.launch_test` and to your journey's scenario arguments.

## Workload options

| Option | Meaning | Default |
| --- | --- | --- |
| `--users` | Target number of virtual users. | `1` |
| `--spawn_rate` | New users per second. | `1` |
| `--runtime` | Maximum runtime per test, in seconds. | `120` |
| `--iterations` | Total task iterations across all users; stop when this or runtime is reached. | `0` (no iteration limit) |
| `--shape` | Load shape, such as `Default` or `Spike`. | `Default` |
| `--scenario_delay` | Pause between YAML scenarios, in seconds. | `0` |

The quickstart overrides these defaults in `pytest.ini` with three users and a
three-second runtime. Command-line settings, including that `addopts` line, take
precedence over YAML and environment settings. **Remove the quickstart's `addopts`
line before trying the YAML or environment examples below.**

List all options with `pytest --help` after
[configuring pytest](writing-tests.md#configure-pytest). Load shapes
can override workload settings; see the [available shapes](../src/grasshopper/lib/util/shapes.py).

## YAML scenarios

Keep scenarios beside your test file. For the copied quickstart, save this as
`scenarios.yaml`:

```yaml
smoke:
  test_file_name: test_performance.py
  grasshopper_args:
    users: 1
    spawn_rate: 1
    runtime: 3
  tags: [smoke]

load:
  test_file_name: test_performance.py
  grasshopper_args:
    users: 10
    spawn_rate: 5
    runtime: 10
  tags: [load]
```

From that directory, select one workload for the Python test file:

```shell
pytest test_performance.py --scenario_file=scenarios.yaml --scenario_name=smoke
```

Or ask Grasshopper to collect the YAML file and select scenarios by tag:

```shell
pytest scenarios.yaml --tags=smoke
```

Without `--tags`, every scenario in the file runs. Each scenario name is also an
implicit tag. Tag expressions use [tag-matcher](https://pypi.org/project/tag-matcher/).
Each selected scenario runs the test file, including its parametrized test cases.

Use `grasshopper_scenario_args` for application-specific values. The
[extended scenario example](../example/example_scenarios.YAML) also shows weighted
composite journeys and argument overrides. Adapt its external target before use.

## Configuration precedence

When the same key appears in several places, the first source in this list wins:

1. Command-line arguments.
2. Environment variables.
3. The selected YAML scenario.
4. A Grasshopper configuration file.
5. Framework defaults.

Read values by lowercase key, for example `complete_configuration["users"]`.
Built-in environment settings use uppercase names such as `USERS` and `RUNTIME`:

```shell
USERS=5 RUNTIME=10 pytest
```

Custom environment values use the `GH_` prefix: `GH_TENANT_ID=demo` becomes
`complete_configuration["tenant_id"]`. To integrate existing environment names,
override the `extra_env_var_keys` fixture with a list of names, or
`env_var_prefix_key` with a different prefix string.

## Shared configuration files

For settings shared across scenarios, add this fixture to `conftest.py`:

```python
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def grasshopper_config_file_path() -> str:
    return str(Path(__file__).with_name("grasshopper.yaml"))
```

A `grasshopper.yaml` file can group settings under `grasshopper` (integrations),
`test_run` (workload), and `scenario` (application values). Only the sections you
need are required:

```yaml
test_run:
  users: 5
  runtime: 10
scenario:
  tenant_id: demo
```

For custom command-line options, use pytest's `pytest_addoption` hook and read the
value in a fixture, then pass it into the journey. The
[configuration fixture example](../example/conftest.py) demonstrates this pattern.
Thresholds accept dictionaries in Python/YAML and JSON strings in command-line
or environment settings; see [timing thresholds](checks-and-reporting.md#timing-thresholds).
