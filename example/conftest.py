"""Short demo defaults that YAML, environment variables, and CLI options can override."""

import pytest
from grasshopper.lib.configuration.gh_configuration import GHConfiguration


@pytest.fixture(scope="session")
def global_defaults(global_defaults: GHConfiguration) -> GHConfiguration:
    """Extend Grasshopper's defaults without overriding explicit workload settings."""
    return GHConfiguration(global_defaults, users=1, spawn_rate=1, runtime=3)
