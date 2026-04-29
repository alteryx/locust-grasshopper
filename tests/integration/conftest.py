"""Module: Contest.py.

Conftest for use with integration tests for Grasshopper.

"""

# IMPORTANT: gevent monkey patching must happen before any other imports
# to avoid SSL-related RecursionError issues with locust
from gevent import monkey

monkey.patch_all()

import os  # noqa: E402

# import pytest

GRASSHOPPER_CONFIG_FILE_PATH = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), "grasshopper.config"
)

# Leaving this here because sometimes we want to turn it on for testing, but we don't
# want to use a config file unless the grasshopper consumer supplies one
# @pytest.fixture(scope="session")
# def grasshopper_config_file_path():
#     return GRASSHOPPER_CONFIG_FILE_PATH
