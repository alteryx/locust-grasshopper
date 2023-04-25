"""Grasshopper Framework Package.

Owned by Team Shield.

Package for framework that combines locust, pytest and some supporting utilities to
provide a fully featured, python based load testing options for API clients.

Note that the only things we want handled in this setup method is setting the version,
the only thing that we are currently doing dynamically (in this case version).
All other configuration for the package is located in the setup.cfg, per the most recent
guidance on python packaging best practices:
https://packaging.python.org/en/latest/tutorials/packaging-projects/

"""
from setuptools import setup

setup(
    entry_points={"pytest11": ["locust_grasshopper = grasshopper.lib.fixtures"]},
)
