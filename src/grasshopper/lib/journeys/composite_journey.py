"""Module: BaseJourney.

Class to hold all the common functionality that we added on top of Locust's HttpUser
class.
"""
import os

import pytest

import grasshopper.lib.util.listeners  # noqa: F401
from grasshopper.lib.grasshopper import Grasshopper

FILE_PATH = os.path.basename(__file__)


@pytest.fixture
def weighted_user_classes():
    classes = {}
    return classes


def test_run_composite(
    complete_configuration,
    weighted_user_classes,
):
    """The generalized test function for running composite journeys in Grasshopper."""
    locust_env = Grasshopper.launch_test(
        weighted_user_classes, **complete_configuration
    )
    return locust_env
