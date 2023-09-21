"""Module: test_gh_composite.

The generalized test function for running composite journeys in Grasshopper.
"""
import os

import grasshopper.lib.util.listeners  # noqa: F401
from grasshopper.lib.grasshopper import Grasshopper

FILE_PATH = os.path.basename(__file__)


def test_run_composite(
    complete_configuration,
    composite_weighted_user_classes,
):
    """The generalized test function for running composite journeys in Grasshopper."""
    for user_class in composite_weighted_user_classes.keys():
        user_class.update_incoming_scenario_args(complete_configuration)
    locust_env = Grasshopper.launch_test(
        composite_weighted_user_classes, **complete_configuration
    )
    return locust_env
