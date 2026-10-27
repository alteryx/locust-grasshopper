# Configure Locust/pytest load tests and YAML scenarios

[Project overview](../README.md) · [Writing tests](writing-tests.md) ·
[Checks and reporting](checks-and-reporting.md)

Grasshopper merges workload and application settings into the
`complete_configuration` pytest fixture, a dictionary-like `GHConfiguration`.
Pass it to `Grasshopper.launch_test` to configure the workload.

## Workload options

| Option | Meaning | Default |
| --- | --- | --- |
| `--users` | Target number of virtual users. | `1` |
| `--spawn_rate` | New users per second. | `1` |
| `--runtime` | Maximum runtime per test, in seconds. | `120` |
| `--iterations` | Total task iterations across all users; stop when this or runtime is reached. | `0` (no iteration limit) |
| `--shape` | Load shape, such as `Default` or `Spike`. | `Default` |
| `--scenario_delay` | Pause between YAML scenarios, in seconds. | `0` |

The quickstart's [conftest.py](../example/conftest.py) overrides the `global_defaults`
fixture to use one user and a three-second runtime. YAML, environment variables,
and CLI options override those demo defaults without editing `pytest.ini`.

List all options with `pytest --help` after
[configuring pytest](writing-tests.md#configure-pytest). Load shapes
can override workload settings; see the [available shapes](../src/grasshopper/lib/util/shapes.py).

## YAML scenarios

Keep scenarios beside your test file. The quickstart includes
[example_scenarios.YAML](../example/example_scenarios.YAML):

```yaml
smoke:
  test_file_name: test_example.py
  grasshopper_args:
    users: 1
    spawn_rate: 1
    runtime: 3
  tags: [smoke]

iterations:
  test_file_name: test_example.py
  grasshopper_args:
    users: 1
    spawn_rate: 1
    runtime: 10
    iterations: 3
  tags: [iterations]
```

From that directory, select one workload for the Python test file:

```shell
pytest test_example.py --scenario_file=example_scenarios.YAML --scenario_name=smoke
```

Or ask Grasshopper to collect the YAML file and select scenarios by tag:

```shell
pytest example_scenarios.YAML --tags=smoke
```

Without `--tags`, every scenario in the file runs. Each scenario name is also an
implicit tag. Tag expressions use [tag-matcher](https://pypi.org/project/tag-matcher/).
Each selected scenario runs the test file, including its parametrized test cases.

The `iterations` scenario stops after three task iterations or ten seconds,
whichever comes first. Both examples keep the public API workload small.
Use `grasshopper_scenario_args` for application-specific values, as described below.

## Journey settings

Journey `defaults` define application settings and thresholds in code. If your
journey needs values from YAML, environment variables, or a configuration file,
pass them to the journey before launching:

```python
ExampleJourney.replace_incoming_scenario_args(complete_configuration)
environment = Grasshopper.launch_test(ExampleJourney, **complete_configuration)
```

Inside the journey, read values through `self.scenario_args`, for example
`self.scenario_args["tenant_id"]`. Incoming settings override the journey's defaults.

## Configuration precedence

When the same key appears in several places, the first source in this list wins:

1. Command-line arguments.
2. Environment variables.
3. The selected YAML scenario.
4. A Grasshopper configuration file.
5. The `global_defaults` fixture (framework or suite defaults).

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
value in a fixture, then pass it into the journey.
Thresholds accept dictionaries in Python/YAML and JSON strings in command-line
or environment settings; see [timing thresholds](checks-and-reporting.md#timing-thresholds).
