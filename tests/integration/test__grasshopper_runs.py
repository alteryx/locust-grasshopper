import logging
import random

import pytest
from assertpy import assert_that
from requests import Request
from requests_mock import ANY

from tests.unit.conftest import (  # noqa: I202
    calculate_path,
    perform_fixture_test_with_optional_log_capture,
    was_message_logged,
)

logger = logging.getLogger(__name__)

MIN_NUMBER_OF_REQUESTS = 10


@pytest.fixture(scope="session")
def std_gh_output_msgs():
    cfg_start_msg = {
        "target_level": logging.INFO,
        "target_message_re": "-+ Grasshopper configuration -+",
    }
    cfg_end_msg = {
        "target_level": logging.INFO,
        "target_message_re": "-+ /Grasshopper configuration -+",
    }
    threshold_msg = {
        "target_level": logging.INFO,
        "target_message_re": "-+ THRESHOLD REPORT -+",
    }
    checks_msg = {
        "target_level": logging.INFO,
        "target_message_re": "-+ CHECKS REPORT -+",
    }

    return [
        cfg_start_msg,
        cfg_end_msg,
        threshold_msg,
        checks_msg,
    ]


@pytest.fixture
def std_gh_out_with_cfg_msgs(std_gh_output_msgs):
    expected = std_gh_output_msgs.copy()
    cfg_shape_msg = {
        "target_level": logging.INFO,
        "target_message_re": r"shape: \[Default\]",
    }
    cfg_users_msg = {
        "target_level": logging.INFO,
        "target_message_re": r"users: \[\d+\]",
    }
    cfg_runtime_msg = {
        "target_level": logging.INFO,
        "target_message_re": r"runtime: \[\d+\]",
    }
    cfg_spawn_msg = {
        "target_level": logging.INFO,
        "target_message_re": r"spawn_rate: \[\d+\.\d+\]",
    }
    cfg_delay_msg = {
        "target_level": logging.INFO,
        "target_message_re": r"scenario_delay: \[\d+\.\d+\]",
    }
    cfg_shape_instances_msg = {
        "target_level": logging.INFO,
        "target_message_re": r"shape_instance: \[<grasshopper.lib.util.shapes.Default "
        r"object at (.+)>\]",
    }
    cfg_user_classes_msg = {
        "target_level": logging.INFO,
        "target_message_re": r"user_classes: "
        r"\[{<class 'test__journey1.Journey1'>: 1}\]",
    }

    expected.append(cfg_user_classes_msg)
    expected.append(cfg_shape_instances_msg)
    expected.append(cfg_users_msg)
    expected.append(cfg_runtime_msg)
    expected.append(cfg_delay_msg)
    expected.append(cfg_spawn_msg)
    expected.append(cfg_shape_msg)

    return expected


@pytest.fixture
def expected_output_messages(std_gh_out_with_cfg_msgs):
    expected = std_gh_out_with_cfg_msgs.copy()
    check_failed_msg = {
        "target_level": logging.WARNING,
        "target_message_re": "Check failed: Status code is good",
    }
    expected.append(check_failed_msg)
    return expected


@pytest.fixture
def mock_requests_get_mix_status_codes(requests_mock):
    def response_provider_mix_of_status_codes(request: Request, context):
        context.status_code = random.choice([200, 200, 200, 201, 403, 500])
        return {"data": f"mocked response {context.status_code}"}

    requests_mock.get(ANY, json=response_provider_mix_of_status_codes)
    return requests_mock


def test__grasshopper__running_with_config_defaults(
    pytester,
    caplog,
    expected_output_messages,
    mock_requests_get_mix_status_codes,
):
    """Cover running a grasshopper test with the defaults.

    These are the configuration values you would get if you simply ran `pytest` in the
    directory where this journey file was located.

    """
    dummy_journey_file = calculate_path(
        "test__journey1.py", subdir="../integration_testing_data"
    )

    pytester.copy_example(dummy_journey_file)
    perform_fixture_test_with_optional_log_capture(
        pytester, caplog=caplog, target_messages=expected_output_messages
    )

    # assert that the requests_mock was called a reasonable number of times
    assert_that(mock_requests_get_mix_status_codes.call_count).is_greater_than(
        MIN_NUMBER_OF_REQUESTS
    )

    # check that a reasonable number of messages coming from the @task are in caplog
    _, starting_msgs = was_message_logged(
        caplog=caplog,
        target_message_re=r"VU \d+: Starting journey1_task",
        target_level=logging.INFO,
    )
    assert_that(
        len(starting_msgs), f"Actual contents of msg list {starting_msgs}"
    ).is_greater_than(MIN_NUMBER_OF_REQUESTS)
    _, return_msgs = was_message_logged(
        caplog=caplog,
        target_message_re=r"VU \d+: Google result: [200|403|500]",
        target_level=logging.INFO,
    )
    assert_that(
        len(return_msgs), f"Actual contents of msg list {return_msgs}"
    ).is_greater_than(MIN_NUMBER_OF_REQUESTS)
