"""Build package metadata with absolute README links for PyPI."""

import re
from pathlib import Path
from urllib.parse import urljoin

from setuptools import setup

setup(
    long_description=re.sub(
        r"(?<=\]\()[^)]+(?=\))",
        lambda match: urljoin(
            "https://github.com/alteryx/locust-grasshopper/blob/main/README.md",
            match.group(),
        ),
        Path(__file__).with_name("README.md").read_text(encoding="utf-8"),
    ),
    long_description_content_type="text/markdown",
    entry_points={"pytest11": ["locust_grasshopper = grasshopper.lib.fixtures"]},
)
