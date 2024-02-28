import time
from unittest.mock import MagicMock

import pytest
from grasshopper.lib.fixtures.grasshopper_constants import GrasshopperConstants
from grasshopper.lib.util.check_constants import CheckConstants
from grasshopper.lib.util.listeners import GrasshopperListeners
from grasshopper.lib.util.utils import (
    check,
    current_method_name,
    custom_trend,
    highlight_print,
    logger,
    report_checks_to_console,
    report_thresholds_to_console,
)
from termcolor import colored


@pytest.fixture
def example_trends_dict():
    trends = {
        "Trend One": {
            "thresholds": [
                {
                    "percentile": GrasshopperConstants.THRESHOLD_PERCENTILE_DEFAULT,
                    "less_than_in_ms": 1000,
                    "actual_value_in_ms": 600,
                    "http_method": "CUSTOM",
                },
                {
                    "percentile": GrasshopperConstants.THRESHOLD_PERCENTILE_DEFAULT,
                    "less_than_in_ms": 1000,
                    "actual_value_in_ms": 1200,
                    "http_method": "CUSTOM",
                },
            ]
        },
        "Trend Two": {
            "thresholds": [
                {
                    "percentile": GrasshopperConstants.THRESHOLD_PERCENTILE_DEFAULT,
                    "less_than_in_ms": 2000,
                    "actual_value_in_ms": 1400,
                    "http_method": "CUSTOM",
                },
                {
                    "percentile": GrasshopperConstants.THRESHOLD_PERCENTILE_DEFAULT,
                    "less_than_in_ms": 2000,
                    "actual_value_in_ms": 2800,
                    "http_method": "CUSTOM",
                },
            ]
        },
    }
    return trends


@pytest.fixture
def example_checks_dict():
    checks = {
        "Passing": {
            "passed": 3,
            "failed": 0,
            "total": 3,
            "verdict": CheckConstants.VERDICT_ALL_PASSED,
            "percentage_passed_display": "100.0%",
            "warning_threshold": 1,
        },
        "Failing": {
            "passed": 0,
            "failed": 3,
            "total": 3,
            "verdict": CheckConstants.VERDICT_FAILED,
            "percentage_passed_display": "0.0%",
            "warning_threshold": 1,
        },
        "Warning": {
            "passed": 2,
            "failed": 1,
            "total": 3,
            "verdict": CheckConstants.VERDICT_PASSED_RATE_OVER_THRESHOLD,
            "percentage_passed_display": "66.67%",
            "warning_threshold": 0.5,
        },
    }
    return checks


@pytest.fixture
def mock_logging(monkeypatch):
    logging_mock = MagicMock()
    monkeypatch.setattr(logger, "info", logging_mock)
    monkeypatch.setattr(logger, "error", logging_mock)
    monkeypatch.setattr(logger, "warning", logging_mock)
    monkeypatch.setattr(logger, "fatal", logging_mock)
    monkeypatch.setattr(logger, "debug", logging_mock)
    return logging_mock


def run_trend(environment, trend_name, func):
    @custom_trend(trend_name)
    def runner(env):
        func(env)

    return runner(environment)


def test_basic_checks(mock_logging: MagicMock):
    """
    A check will add the correct data to the environment.stats.checks dictionary.
    Each check should have a dictionary of its own with the check name as the key.
    If the "checks" dictionary does not exist, one will be created.
    """
    env = MagicMock()
    del env.stats.checks

    check("Sample 1", True, env=env)
    expected = {
        "Sample 1": {"passed": 1, "failed": 0, "total": 1, "warning_threshold": 0.95}
    }
    assert env.stats.checks == expected
    mock_logging.assert_not_called()

    check("Sample 2", False, env=env)
    expected = {
        "Sample 1": {"passed": 1, "failed": 0, "total": 1, "warning_threshold": 0.95},
        "Sample 2": {"passed": 0, "failed": 1, "total": 1, "warning_threshold": 0.95},
    }
    assert env.stats.checks == expected
    mock_logging.assert_called_once_with("Check failed: Sample 2")


def test_stacking_checks():
    """
    A check will look for a pre-existing check of the same name and add data there.
    A check will not overwrite or increment the data of another check.
    """
    env = MagicMock()

    check("Sample 1", True, env=env)
    check("Sample 1", False, env=env)
    expected = {
        "Sample 1": {"passed": 1, "failed": 1, "total": 2, "warning_threshold": 0.95}
    }
    assert env.stats.checks == expected

    check("Sample 2", True, env=env)
    expected = {
        "Sample 1": {"passed": 1, "failed": 1, "total": 2, "warning_threshold": 0.95},
        "Sample 2": {"passed": 1, "failed": 0, "total": 1, "warning_threshold": 0.95},
    }
    assert env.stats.checks == expected

    check("Sample 1", True, env=env)
    expected = {
        "Sample 1": {"passed": 2, "failed": 1, "total": 3, "warning_threshold": 0.95},
        "Sample 2": {"passed": 1, "failed": 0, "total": 1, "warning_threshold": 0.95},
    }
    assert env.stats.checks == expected


def test_check_warning():
    """
    Check warnings will be properly set.
    """
    env = MagicMock()
    check("Warning value set", True, env=env, flexible_warning=0.5)
    assert env.stats.checks["Warning value set"]["warning_threshold"] == 0.5


def test_check_failure_message(mock_logging):
    """
    Check that (optional) failure messages are logged.
    """
    env = MagicMock()
    check("Test logging message", False, env=env, msg_on_failure="Test logging message")
    mock_logging.assert_called_with("Failure message: Test logging message")


def test_check_halt(mock_logging):
    """
    A failing check will stop further execution if halt_on_failure is True.
    """
    env = MagicMock()
    check("Testing halt_on_failure", False, env=env, halt_on_failure=True)
    mock_logging.assert_called_with(
        "Check failed with halt_on_failure enabled. Stopping runner"
    )
    env.runner.quit.assert_called_once()


def test_new_trend_payload():
    """
    A trend will fire an event with the proper attributes, as well as a
    correct response time.
    """

    mock = MagicMock()
    fire = mock.environment.events.request.fire
    expected = {
        # response_time not included, since we can't predict the value
        "request_type": "CUSTOM",
        "name": "test_sleep_100_ms",
        "response_time": 0,
        "response_length": 0,
        "response": None,
        "context": {},
        "exception": None,
    }

    run_trend(mock, "test_sleep_100_ms", lambda a: time.sleep(0.1))

    fire.assert_called_once()
    assert expected.keys() <= fire.call_args.kwargs.keys()


def test_initialize():
    """
    Should set the test start and stop.
    """
    mock = MagicMock()
    env = mock.parent.environment
    GrasshopperListeners(environment=env)

    env.events.test_start.add_listener.assert_called_once()
    env.events.test_stop.add_listener.assert_called_once()


def test_current_method_name():
    assert current_method_name() == "test_current_method_name"


def test_highlight_print(mock_logging):
    highlight_print("Testing highlighted print")
    expected = colored("Testing highlighted print", "green", attrs=["bold"])
    mock_logging.assert_called_with(expected)


def test_threshold_console_output(mock_logging, example_trends_dict):
    # This would be set in _append_trend_data
    example_trends_dict["Trend One"]["thresholds"][0]["succeeded"] = True
    example_trends_dict["Trend One"]["thresholds"][1]["succeeded"] = False
    example_trends_dict["Trend Two"]["thresholds"][0]["succeeded"] = True
    example_trends_dict["Trend Two"]["thresholds"][1]["succeeded"] = False

    report_thresholds_to_console(example_trends_dict)

    call_strings = [
        "-------------------------------- THRESHOLD REPORT "
        "--------------------------------",
        "{:<45} {:<10} {:<10} {:<10}".format(
            "Trend_Name", "Percentile", "Limit", "Actual"
        ),
        colored(
            "{:<45} {:<10} {:<10} {:<10}".format("Trend One", 90, "1000ms", "600ms"),
            "green",
            attrs=["bold"],
        ),
        colored(
            "{:<45} {:<10} {:<10} {:<10}".format("Trend One", 90, "1000ms", "1200ms"),
            "red",
            attrs=["bold"],
        ),
        colored(
            "{:<45} {:<10} {:<10} {:<10}".format("Trend Two", 90, "2000ms", "1400ms"),
            "green",
            attrs=["bold"],
        ),
        colored(
            "{:<45} {:<10} {:<10} {:<10}".format("Trend Two", 90, "2000ms", "2800ms"),
            "red",
            attrs=["bold"],
        ),
    ]
    for i in range(len(call_strings)):
        assert mock_logging.call_args_list[i][0][0] == call_strings[i]


def test_checks_console_output(mock_logging, example_checks_dict):
    report_checks_to_console(example_checks_dict)
    call_strings = [
        "------------------------------------------------------- CHECKS REPORT "
        "-------------------------------------------------------",
        "{:<80} {:<10} {:<10} {:<10} {:<10}".format(
            "Check_Name", "Passed", "Failed", "Total", "Percentage"
        ),
        colored(
            "{:<80} {:<10} {:<10} {:<10} {:<10}".format("Passing", 3, 0, 3, "100.0%"),
            "green",
            attrs=["bold"],
        ),
        colored(
            "{:<80} {:<10} {:<10} {:<10} {:<10}".format("Failing", 0, 3, 3, "0.0%"),
            "red",
            attrs=["bold"],
        ),
        colored(
            "{:<80} {:<10} {:<10} {:<10} {:<10}".format("Warning", 2, 1, 3, "66.67%"),
            "yellow",
            attrs=["bold"],
        ),
    ]
    for i in range(len(call_strings)):
        assert mock_logging.call_args_list[i][0][0] == call_strings[i]


def test_append_trend_data(mock_logging, example_trends_dict):
    env = MagicMock()
    listeners = GrasshopperListeners(environment=env)
    listeners._append_trend_data(env)
    mock_logging.assert_called_with("No threshold data to report.")
    mock_logging.reset_mock()

    env.stats.trends = example_trends_dict
    attrs = {"get_response_time_percentile.return_value": 1100}
    env.stats.get = MagicMock(return_value=MagicMock(**attrs))
    listeners._append_trend_data(env)
    assert mock_logging.call_count == 7


def test_append_checks_data(mock_logging, example_checks_dict):
    env = MagicMock()
    listeners = GrasshopperListeners(environment=env)
    listeners._append_checks_data(env)
    mock_logging.assert_called_with("No checks data to report.")
    mock_logging.reset_mock()

    env.stats.checks = example_checks_dict
    listeners._append_checks_data(env)
    assert mock_logging.call_count == 6
