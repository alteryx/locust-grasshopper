from unittest.mock import MagicMock, call

import pytest
from assertpy import assert_that
from grasshopper.lib.reporting.reporter_extensions import (
    IExtendedReporter,
    ReporterExtensions,
)
from grasshopper.lib.util.utils import epoch_time
from locust import env as locust_environment


@pytest.fixture(scope="function", autouse=True)
def clear_class_registrations():
    ReporterExtensions.clear_registrations()


@pytest.fixture
def mock_er_1():
    mock_er = MagicMock(spec=IExtendedReporter)
    mock_er.get_name.return_value = "magicmock er #1"
    return mock_er


@pytest.fixture
def mock_er_2():
    mock_er = MagicMock(spec=IExtendedReporter)
    mock_er.get_name.return_value = "magicmock er #2"
    return mock_er


@pytest.fixture
def mock_er_3():
    mock_er = MagicMock(spec=IExtendedReporter)
    mock_er.get_name.return_value = "magicmock er #3"
    return mock_er


@pytest.fixture
def mock_er_invalid():
    mock_er = MagicMock()
    mock_er.get_name.side_effect = AttributeError
    return mock_er


def test__registration_happy(mock_er_1):
    ReporterExtensions.register_er(mock_er_1)
    assert_that(ReporterExtensions.ers).is_length(1)
    assert_that(ReporterExtensions.registrations).is_length(1)
    assert_that(ReporterExtensions.registrations).contains(mock_er_1.get_name())


def test__registration_invalid(mock_er_1, mock_er_invalid):
    ReporterExtensions.register_er(mock_er_1)
    ReporterExtensions.register_er(mock_er_invalid)
    assert_that(ReporterExtensions.ers).is_length(1)
    assert_that(ReporterExtensions.registrations).is_length(1)
    assert_that(ReporterExtensions.registrations).contains(mock_er_1.get_name())


def test__registration_multiple(mock_er_1, mock_er_2, mock_er_3):
    ReporterExtensions.register_er(mock_er_1)
    ReporterExtensions.register_er(mock_er_2)
    ReporterExtensions.register_er(mock_er_3)
    assert_that(ReporterExtensions.ers).is_length(3)
    assert_that(ReporterExtensions.registrations).is_length(3)
    assert_that(ReporterExtensions.registrations).contains(mock_er_1.get_name())
    assert_that(ReporterExtensions.registrations).contains(mock_er_2.get_name())
    assert_that(ReporterExtensions.registrations).contains(mock_er_3.get_name())


def test__unregister_happy(mock_er_1):
    ReporterExtensions.register_er(mock_er_1)
    assert_that(ReporterExtensions.registrations).is_length(1)
    ReporterExtensions.unregister_er(mock_er_1.get_name())
    assert_that(ReporterExtensions.registrations).is_length(0)


def test__unregister_multiple(mock_er_1, mock_er_2, mock_er_3):
    ReporterExtensions.register_er(mock_er_1)
    ReporterExtensions.register_er(mock_er_2)
    ReporterExtensions.register_er(mock_er_3)
    assert_that(ReporterExtensions.registrations).is_length(3)
    ReporterExtensions.unregister_er(mock_er_2.get_name())
    assert_that(ReporterExtensions.registrations).is_length(2)
    assert_that(ReporterExtensions.registrations).contains(mock_er_1.get_name())
    assert_that(ReporterExtensions.registrations).contains(mock_er_3.get_name())


def test__unregister_empty():
    ReporterExtensions.unregister_er("non existent er")


def test__unregister_not_registered(mock_er_1):
    ReporterExtensions.register_er(mock_er_1)
    assert_that(ReporterExtensions.registrations).is_length(1)
    # checking that no errors are raised on the unregister and also that the contents
    # of the registrations were not affected
    ReporterExtensions.unregister_er("non existent er")
    assert_that(ReporterExtensions.registrations).is_length(1)


def test__notify_pre_test_happy(mock_er_1, mock_er_2):
    ReporterExtensions.register_er(mock_er_1)
    ReporterExtensions.register_er(mock_er_2)
    test_name = "fake test"
    start_epoch = epoch_time()
    test_args = {"key": "value"}
    ReporterExtensions.notify_pre_test(test_name, start_epoch, test_args=test_args)
    mock_er_1.event_pre_test.assert_called_once_with(
        test_name, start_epoch, test_args=test_args
    )
    mock_er_2.event_pre_test.assert_called_once_with(
        test_name, start_epoch, test_args=test_args
    )


def test__notify_post_test_happy(mock_er_1, mock_er_2):
    ReporterExtensions.register_er(mock_er_1)
    ReporterExtensions.register_er(mock_er_2)
    test_name = "fake test"
    start_epoch = epoch_time()
    end_epoch = start_epoch + 1000
    test_args = {"key": "value"}
    locust_mock = MagicMock(spec=locust_environment)
    ReporterExtensions.notify_post_test(
        test_name, start_epoch, end_epoch, locust_mock, test_args=test_args
    )
    mock_er_1.event_post_test.assert_called_once_with(
        test_name, start_epoch, end_epoch, locust_mock, test_args=test_args
    )
    mock_er_2.event_post_test.assert_called_once_with(
        test_name, start_epoch, end_epoch, locust_mock, test_args=test_args
    )


def test__notify_post_test_multiple_events(mock_er_1, mock_er_2):
    ReporterExtensions.register_er(mock_er_1)
    ReporterExtensions.register_er(mock_er_2)
    test_name = "fake test"
    start_epoch = epoch_time()
    end_epoch = start_epoch + 1000
    test_args = {"key": "value"}
    locust_mock = MagicMock(spec=locust_environment)
    ReporterExtensions.notify_post_test(
        test_name, start_epoch, end_epoch, locust_mock, test_args=test_args
    )
    test_name2 = "fake test 2"
    ReporterExtensions.notify_post_test(
        test_name2, start_epoch, end_epoch, locust_mock, test_args=test_args
    )
    calls = [
        call(test_name, start_epoch, end_epoch, locust_mock, test_args=test_args),
        call(test_name2, start_epoch, end_epoch, locust_mock, test_args=test_args),
    ]
    mock_er_1.event_post_test.assert_has_calls(calls, any_order=True)
    mock_er_2.event_post_test.assert_has_calls(calls, any_order=True)


def test__notify_pre_suite_happy(mock_er_1, mock_er_2):
    ReporterExtensions.register_er(mock_er_1)
    ReporterExtensions.register_er(mock_er_2)
    suite_name = "fake suite"
    start_epoch = epoch_time()
    suite_args = {"key": "value"}
    ReporterExtensions.notify_pre_suite(suite_name, start_epoch, suite_args=suite_args)
    mock_er_1.event_pre_suite.assert_called_once_with(
        suite_name, start_epoch, suite_args=suite_args
    )
    mock_er_2.event_pre_suite.assert_called_once_with(
        suite_name, start_epoch, suite_args=suite_args
    )


def test__notify_post_suite_happy(mock_er_1, mock_er_2):
    ReporterExtensions.register_er(mock_er_1)
    ReporterExtensions.register_er(mock_er_2)
    suite_name = "fake suite"
    start_epoch = epoch_time()
    end_epoch = start_epoch + 1000
    suite_args = {"key": "value"}
    ReporterExtensions.notify_post_suite(
        suite_name, start_epoch, end_epoch, suite_args=suite_args
    )
    mock_er_1.event_post_suite.assert_called_once_with(
        suite_name, start_epoch, end_epoch, suite_args=suite_args
    )
    mock_er_2.event_post_suite.assert_called_once_with(
        suite_name, start_epoch, end_epoch, suite_args=suite_args
    )


def test__notify_empty():
    test_name = "fake test"
    start_epoch = epoch_time()
    test_args = {"key": "value"}
    # checking to make sure that no errors are raised if a notify event happens and
    # the registrations are empty
    ReporterExtensions.notify_pre_test(test_name, start_epoch, test_args=test_args)


def test__notify_extra_kwargs(mock_er_1):
    ReporterExtensions.register_er(mock_er_1)
    test_name = "fake test"
    start_epoch = epoch_time()
    test_args = {"key1": "value1"}
    ReporterExtensions.notify_pre_test(
        test_name, start_epoch, test_args=test_args, key2="value2"
    )
    # this is checking that any extra kwargs are being passed on to the event method
    mock_er_1.event_pre_test.assert_called_once_with(
        test_name, start_epoch, test_args=test_args, key2="value2"
    )


def test__notify_event_invalid_event_name(mock_er_1):
    ReporterExtensions.register_er(mock_er_1)
    ReporterExtensions._notify_event("event_that_does_not_exist")
