"""Module: Contest.py.

Conftest for use with integration tests for Grasshopper.

"""
import logging
import os
import random

import gevent
import pytest
from requests import Request
from requests_mock import ANY

pytest_plugins = ["pytester"]

GRASSHOPPER_CONFIG_FILE_PATH = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), "grasshopper.config"
)


@pytest.fixture
def std_gh_output_msgs():
    msgs = [
        construct_msg("-+ Grasshopper configuration -+"),
        construct_msg("-+ THRESHOLD REPORT -+"),
        construct_msg("-+ CHECKS REPORT -+"),
        construct_msg("-+ /Grasshopper configuration -+"),
    ]

    return msgs


@pytest.fixture
def std_gh_out_with_cfg_msgs(std_gh_output_msgs):
    std_gh_output_msgs.append(construct_msg(r"shape: \[Default\]"))
    std_gh_output_msgs.append(construct_msg(r"users: \[\d+\]"))
    std_gh_output_msgs.append(construct_msg(r"runtime: \[\d+(\.\d+)?\]"))
    std_gh_output_msgs.append(construct_msg(r"spawn_rate: \[\d+\.\d+\]"))
    std_gh_output_msgs.append(construct_msg(r"scenario_delay: \[\d+\.\d+\]"))
    std_gh_output_msgs.append(
        construct_msg(
            r"shape_instance: \[<grasshopper.lib.util.shapes.Default object at (.+)>\]"
        )
    )
    std_gh_output_msgs.append(
        construct_msg(r"user_classes: \[{<class 'test__journey1.Journey1'>: 1}\]")
    )
    return std_gh_output_msgs


@pytest.fixture
def gh_out_add_trends_and_checks(std_gh_out_with_cfg_msgs):
    trend_base = r"\s+\d\d\s+(\d+)ms\s+(\d+)ms"
    check_base = r"\s+\d+\s+\d+\s+\d+\s+\d+(\.\d+)?"

    std_gh_out_with_cfg_msgs.append(construct_msg("PX_TREND_google_home" + trend_base))
    std_gh_out_with_cfg_msgs.append(construct_msg("google_home" + trend_base))
    std_gh_out_with_cfg_msgs.append(construct_msg("Status code is good" + check_base))

    return std_gh_out_with_cfg_msgs


@pytest.fixture
def expected_output_messages(gh_out_add_trends_and_checks):
    gh_out_add_trends_and_checks.append(
        construct_msg("Check failed: Status code is good", target_level=logging.WARNING)
    )
    return gh_out_add_trends_and_checks


@pytest.fixture
def expected_output_messages_add_yaml_specific_cfg(expected_output_messages):
    expected_output_messages.append(
        construct_msg(r"scenario_test_file_name: \[test__journey1.py\]")
    )
    expected_output_messages.append(
        construct_msg(r"scenario_tags: \[\['smoke', 'trend'\]\]")
    )
    expected_output_messages.append(
        construct_msg(r"scenario_file: \[.*scenario(s)?.yaml\]")
    )
    expected_output_messages.append(construct_msg(r"scenario_name: \[scenario\d+\]"))
    return expected_output_messages


def construct_msg(msg_re, target_level=logging.INFO):
    """Construct a message dictionary, for use with validation."""
    msg = {
        "target_level": target_level,
        "target_message_re": msg_re,
    }
    return msg


@pytest.fixture
def mock_requests_get_mix_status_codes(requests_mock):
    def response_provider_mix_of_status_codes(request: Request, context):
        context.status_code = random.choice([200, 200, 200, 201, 403, 500])
        sleep_time = random.randint(1, 3) / 10
        gevent.sleep(sleep_time)
        return {"data": f"mocked response {context.status_code}"}

    requests_mock.get(ANY, json=response_provider_mix_of_status_codes)
    return requests_mock
