import logging

from assertpy import assert_that

from tests.integration.conftest import construct_msg  # noqa: I202
from tests.unit.conftest import (  # noqa: I202
    calculate_path,
    perform_pytester_test_with_optional_log_capture,
    was_message_logged,
)

logger = logging.getLogger(__name__)

MIN_NUMBER_OF_REQUESTS = 10


def validate_number_of_iterations(
    caplog, mock_requests, min_iterations=MIN_NUMBER_OF_REQUESTS
):
    # assert that the requests_mock was called a reasonable number of times
    assert_that(mock_requests.call_count).is_greater_than(min_iterations)

    # check that a reasonable number of messages coming from the @task are in caplog
    _, starting_msgs = was_message_logged(
        caplog=caplog,
        target_message_re=r"VU \d+: Starting journey1_task",
        target_level=logging.INFO,
    )
    assert_that(
        len(starting_msgs), f"Actual contents of msg list {starting_msgs}"
    ).is_greater_than(min_iterations)
    _, return_msgs = was_message_logged(
        caplog=caplog,
        target_message_re=r"VU \d+: Google result: [200|403|500]",
        target_level=logging.INFO,
    )
    assert_that(
        len(return_msgs), f"Actual contents of msg list {return_msgs}"
    ).is_greater_than(min_iterations)


def test__grasshopper__py__running_with_config_defaults(
    pytester,
    caplog,
    expected_output_messages,
    mock_requests_get_mix_status_codes,
):
    """Short, but complete, grasshopper run.

    Run directly against a journey py file, using mainly the configuration defaults.
    The non default items added are thresholds (found in the defaults on the class)
    and the runtime has been overridden to be shorter (so that the test isn't too long).

    """
    dummy_journey_file = calculate_path(
        "test__journey1.py", subdir="../integration_testing_data"
    )

    pytester.copy_example(dummy_journey_file)
    perform_pytester_test_with_optional_log_capture(
        pytester,
        target="test__journey1.py",
        args=["--runtime=20"],  # override time so test does not take _too_ long
        caplog=caplog,
        target_messages=expected_output_messages,
    )
    validate_number_of_iterations(caplog, mock_requests_get_mix_status_codes)


def test__grasshopper__yaml__collect_entire_file(
    pytester,
    caplog,
    expected_output_messages_add_yaml_specific_cfg,
    mock_requests_get_mix_status_codes,
):
    """Short, but complete, grasshopper run.

    Run directly against a scenario file, not providing a scenario name.
    There is only one scenario in the scenario file being used.

    Per the grasshopper behavior, the scenario is providing some values that override
    the defaults, but not much that actually changes behavior. Thresholds used are from
    this file.

    Runtime is still being overridden so that the test does not take _too_ long.

    """
    expected_output_messages = expected_output_messages_add_yaml_specific_cfg
    dummy_journey_file = calculate_path(
        "test__journey1.py", subdir="../integration_testing_data"
    )
    dummy_scenario_file = calculate_path(
        "single_scenario.yaml", subdir="../integration_testing_data"
    )

    pytester.copy_example(dummy_journey_file)
    pytester.copy_example(dummy_scenario_file)
    perform_pytester_test_with_optional_log_capture(
        pytester,
        target="single_scenario.yaml",
        args=["--runtime=20"],  # override time so test does not take _too_ long
        caplog=caplog,
        target_messages=expected_output_messages,
    )
    validate_number_of_iterations(caplog, mock_requests_get_mix_status_codes)


def test__grasshopper__yaml__collect_one_scenario(
    pytester,
    caplog,
    expected_output_messages_add_yaml_specific_cfg,
    mock_requests_get_mix_status_codes,
):
    """Short, but complete, grasshopper run.

    Run directly against a scenario file, using tags to select the scenario. Only one
    scenario should match in the file.

    Per the grasshopper behavior, the scenario is providing some values that override
    the defaults, but not much that actually changes behavior. Thresholds used are from
    this file.

    Runtime is still being overridden so that the test does not take _too_ long.

    """
    expected_output_messages = expected_output_messages_add_yaml_specific_cfg
    dummy_journey_file = calculate_path(
        "test__journey1.py", subdir="../integration_testing_data"
    )
    dummy_scenario_file = calculate_path(
        "multiple_scenarios.yaml", subdir="../integration_testing_data"
    )

    pytester.copy_example(dummy_journey_file)
    pytester.copy_example(dummy_scenario_file)

    # this message appears when a scenario is collected
    expected_output_messages.append(
        construct_msg(
            r"Scenarios collected that match the specific tag query `scenario1`: "
            r"\['scenario1'\]"
        )
    )

    perform_pytester_test_with_optional_log_capture(
        pytester,
        target="multiple_scenarios.yaml",
        args=["--runtime=20", "--tags=scenario1"],  # override time, select scenario
        caplog=caplog,
        target_messages=expected_output_messages,
    )
    validate_number_of_iterations(
        caplog,
        mock_requests_get_mix_status_codes,
    )


def test__grasshopper__yaml__collect_multiple(
    pytester,
    caplog,
    expected_output_messages_add_yaml_specific_cfg,
    mock_requests_get_mix_status_codes,
):
    """Short, but complete, grasshopper run.

    Run directly against a scenario file, using tags to select the scenario. The tag
    should select 2 scenarios, which are essentially the same.

    Per the grasshopper behavior, the scenario is providing some values that override
    the defaults, but not much that actually changes behavior. Thresholds used are from
    this file.

    Runtime is still being overridden so that the test does not take _too_ long.

    """
    expected_output_messages = expected_output_messages_add_yaml_specific_cfg
    dummy_journey_file = calculate_path(
        "test__journey1.py", subdir="../integration_testing_data"
    )
    dummy_scenario_file = calculate_path(
        "multiple_scenarios.yaml", subdir="../integration_testing_data"
    )

    pytester.copy_example(dummy_journey_file)
    pytester.copy_example(dummy_scenario_file)

    # this message appears when a scenario is collected
    expected_output_messages.append(
        construct_msg(
            r"Scenarios collected that match the specific tag query `trend`: "
            r"\['scenario1', 'scenario2'\]"
        )
    )

    perform_pytester_test_with_optional_log_capture(
        pytester,
        target="multiple_scenarios.yaml",
        args=["--runtime=20", "--tags=trend"],  # override time, collect 2 scenarios
        outcomes={"passed": 2},
        caplog=caplog,
        target_messages=expected_output_messages,
    )
    validate_number_of_iterations(
        caplog,
        mock_requests_get_mix_status_codes,
        min_iterations=MIN_NUMBER_OF_REQUESTS * 2,
    )
