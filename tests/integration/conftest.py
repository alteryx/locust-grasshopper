"""A file which is used to establish pytest fixtures, plugins, hooks, etc."""

import pytest

from grasshopper.lib.util.utils import highlight_print


def pytest_addoption(parser):
    """Append to existing grasshopper options."""
    parser.addoption(
        "-H",
        "--host",
        action="store",
        default="http://default.url.org",
        help="Base url for test",
    )


@pytest.fixture(scope="function", autouse=True)
def custom_args(request, grasshopper_args):
    # Arguments used by the launch locust code
    args = {"RUN_TIME_PER_TEST": int(grasshopper_args.get("runtime"))}

    # Arguments passed on to locust User class
    args.update({"LOCUST_HOST": request.config.getoption("--host")})

    highlight_print(f"\n\nCustom arguments for this journeys are {args}\n\n")

    return args


@pytest.fixture(scope="session", autouse=True)
def add_workspace_token():

    import os

    hard_coded_token = (
        "eyJ0b2tlbklkIjoiNWVlYWVjZWMtOWE2ZS00OTc1LTlkYjQtNjhmM2Q5Y2Qy"
        "OWMwIiwic2VjcmV0IjoiZjIzNjc0ZTMyOWE4OWMyNmRjNDExYzk5ODQ5M2ZmNz"
        "dkY2IyMDRkNDlmN2NhMTYxMjZjMjg1NjI1NzM4Nzk4ZSJ9"
    )
    os.environ["TRIFACTA_API_TOKEN"] = hard_coded_token

    return os.environ["TRIFACTA_API_TOKEN"]
