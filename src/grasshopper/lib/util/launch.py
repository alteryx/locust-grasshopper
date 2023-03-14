"""Module: Launch.

These are the miscellaneous launch functions for the project that couldn't find
another place to live.
"""
import logging

from locust.env import Environment

from grasshopper.lib.grasshopper import Grasshopper
from grasshopper.lib.util.decorators import deprecate

logger = logging.getLogger()


@deprecate("launch_locust_test", "Grasshopper.launch_test")
def launch_locust_test(user_classes, **kwargs) -> Environment:
    """Launch a locust test, deprecated method."""
    return Grasshopper.launch_test(user_classes, **kwargs)


@deprecate("get_shape_instance", "Grasshopper.load_shape")
def get_shape_instance(shape_name, **kwargs):
    """Get a shape instance, deprecated method."""
    return Grasshopper.load_shape(shape_name, **kwargs)
