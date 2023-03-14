"""A file which is used to establish pytest fixtures, plugins, hooks, etc."""
import pytest
from gevent import monkey

monkey.patch_all()


# ^this part has to be done first in order to avoid errors with importing the requests
# module


def pytest_addoption(parser):
    """Add pytest params."""
    # all grasshopper arguments (users, spawn_rate, etc.) will be automatically
    # loaded via the locust_grasshopper pytest plugin
    # add pytest options that are specific to your tests here
    parser.addoption(
        "--foo", action="store", type=str, help="example parameter", default="bar"
    )


@pytest.fixture(scope="function")
def example_configuration_values(request, grasshopper_args):  # noqa: F811
    """Load all the configuration values for a test."""

    # value defined by this conftest, specific to this particular test
    config_values = {"foo": request.config.getoption("foo")}

    # add in the values coming from grasshopper, if they exist
    config_values.update(grasshopper_args)
    return config_values
