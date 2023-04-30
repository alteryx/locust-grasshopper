"""A file which is used to establish pytest fixtures, plugins, hooks, etc."""
import pytest
from gevent import monkey

monkey.patch_all()
# ^this part has to be done first in order to avoid errors with importing the requests
# module

from grasshopper.lib.configuration.gh_configuration import GHConfiguration  # noqa: E402


def pytest_addoption(parser):
    """Add pytest params."""
    # all grasshopper arguments (users, spawn_rate, etc.) will be automatically
    # loaded via the locust_grasshopper pytest plugin
    # add pytest options that are specific to your tests here
    parser.addoption(
        "--foo", action="store", type=str, help="example parameter", default="bar"
    )


@pytest.fixture(scope="function")
def example_configuration_values(request):  # noqa: F811
    """Load all the configuration values for this specific test (or suite).

    These would be any custom command line values that your test/suite needs and
    would roughly correspond to whatever arguments you added via pytest_addoption hook.

    If you would like to use grasshopper configurations values in calculating these
    values, then you can use the `complete_configuration` fixture to access those.

    You can obviously return whatever you would like from this fixture, but we would
    recommend that you return a GHConfiguration object, which is what all the
    grasshopper configuration code returns (and a Journey is prepared to accept).

    """
    config = GHConfiguration()  # an empty config object

    # value defined by this conftest, specific to this particular test
    config.update_single_key("foo", request.config.getoption("foo"))

    return config
