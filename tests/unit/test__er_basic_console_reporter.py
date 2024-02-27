import logging
from unittest.mock import MagicMock

import pytest
from assertpy import assert_that
from grasshopper.lib.reporting.er_basic_console_reporter import ERBasicConsoleReporter
from grasshopper.lib.util.utils import epoch_time


@pytest.fixture(scope="session", autouse=True)
def capture_logging():
    # this allows for all logging to show up in the fixture caplog
    # caplog.text is just all the text, in one big str
    # caplog.records lists each message logged separately, along with it's level
    logging.root.setLevel(logging.DEBUG)
    logging.root.propagate = True


@pytest.fixture(scope="session")
def fake_suite_args():
    args = {
        "grasshopper_global_args": {
            "slack_webhook": "https://fake_url",
            "rp_token": "fake-token",
        },
        "grasshopper_suite_args": {"runtime": 10, "users": 2},
    }
    return args


@pytest.fixture(scope="session")
def fake_test_args(fake_suite_args):
    args = {
        "suite_args": fake_suite_args,
        "journey_args": {"flow_name": "fake flow", "recipe_id": 1234},
    }
    return args


@pytest.fixture(scope="session")
def fake_passing_threshold():
    threshold = {
        "less_than_in_ms": 1000,
        "actual_value_in_ms": 800,
        "percentile": 0.8,
        "succeeded": True,
        "http_method": "GET",
    }
    return threshold


@pytest.fixture(scope="session")
def fake_thresholds_single(fake_passing_threshold):
    thresholds = [fake_passing_threshold]
    return thresholds


@pytest.fixture(scope="session")
def fake_trends_single_threshold(fake_thresholds_single):
    trends = {"fake trend": {"thresholds": fake_thresholds_single}}
    return trends


@pytest.fixture(scope="session")
def mock_locust_environment(fake_trends_single_threshold):
    mock = MagicMock()
    mock.stats.trends = fake_trends_single_threshold
    return mock


def test__er_basic_console_reporter_name():
    name = ERBasicConsoleReporter.get_name()
    # according to the interface, this method just needs to return a non-zero length
    # string
    assert_that(name).is_type_of(str)
    assert_that(name).is_not_empty()
    new_name = "brand new name"
    # only requirement here is that the er doesn't raise any errors if a notification
    # method should call set_name; note that any given er has the freedom to not do
    # anything when it's called ;) tbh, the set_name method mostly is used for unit
    # testing
    ERBasicConsoleReporter.set_name(new_name)


def test__er_basic_console_reporter_pre_suite(fake_suite_args, caplog):
    start_epoch = epoch_time()
    expected_line_1 = (
        f"Starting Suite fake suite 1 at {start_epoch} with the following arguments:"
    )
    expected_line_2 = (
        "grasshopper_global_args=={'slack_webhook': 'https://fake_url', "
        "'rp_token': 'fake-token'}"
    )
    expected_line_3 = "grasshopper_suite_args=={'runtime': 10, 'users': 2}"
    ERBasicConsoleReporter.event_pre_suite("fake suite 1", start_epoch, fake_suite_args)

    assert_that(caplog.text).contains(expected_line_1, expected_line_2, expected_line_3)


def test__er_basic_console_reporter_post_suite(fake_suite_args, caplog):
    start_epoch = epoch_time()
    end_epoch = start_epoch + 1000
    expected_line_1 = "Suite fake suite 1 complete"
    ERBasicConsoleReporter.event_post_suite(
        "fake suite 1", start_epoch, end_epoch, fake_suite_args
    )

    assert_that(caplog.text).contains(expected_line_1)


def test__er_basic_console_reporter_pre_test(fake_test_args, caplog):
    start_epoch = epoch_time()
    expected_line_1 = (
        f"Starting Test fake test 1 at {start_epoch} with the following arguments:"
    )
    expected_line_2 = (
        "suite_args=={'grasshopper_global_args': {'slack_webhook': "
        "'https://fake_url', 'rp_token': 'fake-token'}, 'grasshopper_suite_args': "
        "{'runtime': 10, 'users': 2}}"
    )
    expected_line_3 = "journey_args=={'flow_name': 'fake flow', 'recipe_id': 1234}"
    ERBasicConsoleReporter.event_pre_test("fake test 1", start_epoch, fake_test_args)

    assert_that(caplog.text).contains(expected_line_1, expected_line_2, expected_line_3)


def test__er_basic_console_reporter_post_test(
    fake_test_args, mock_locust_environment, caplog
):
    start_epoch = epoch_time()
    end_epoch = start_epoch + 1000
    expected_line_1 = (
        f"Test fake test 1 complete at {end_epoch} with the following results:"
    )
    expected_line_2 = f"Epoch time stamp: {start_epoch} - {end_epoch}"
    expected_line_3 = "Trend_Name                     Percentile Limit      Actual    "
    expected_line_4 = "fake trend                     80         1000ms     800ms     "

    ERBasicConsoleReporter.event_post_test(
        "fake test 1", start_epoch, end_epoch, mock_locust_environment, fake_test_args
    )
    # for some reason assert_that is not working correctly for just this one set of
    # messages, so use the standard assert instead
    assert expected_line_1 in caplog.text
    assert expected_line_2 in caplog.text
    assert expected_line_3 in caplog.text
    assert expected_line_4 in caplog.text
