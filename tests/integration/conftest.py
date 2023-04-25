"""Module: Contest.py.

Conftest for use with integration tests for Grasshopper.

"""
import os

# import pytest

GRASSHOPPER_CONFIG_FILE_PATH = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), "grasshopper.config"
)

# Leaving this here because sometimes we want to turn it on for testing, but we don't
# want to use a config file unless the grasshopper consumer supplies one
# @pytest.fixture(scope="session")
# def grasshopper_config_file_path():
#     return GRASSHOPPER_CONFIG_FILE_PATH
