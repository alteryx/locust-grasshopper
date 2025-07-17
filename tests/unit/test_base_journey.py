import logging
from unittest.mock import MagicMock, patch

import pytest
from grasshopper.lib.fixtures.grasshopper_constants import GrasshopperConstants
from grasshopper.lib.journeys.base_journey import BaseJourney


@pytest.fixture(scope="function", autouse=True)
def base_journey():
    BaseJourney.reset_class_attributes()


def test_set_tags_via_defaults():
    journey = BaseJourney(MagicMock())
    journey.defaults = {"tags": {"foo": "bar"}}
    journey.update_incoming_scenario_args({"not tags": "something else"})
    journey._merge_incoming_defaults_and_params()
    assert journey._incoming_test_parameters["tags"] == {"foo": "bar"}


def test_set_tags_none():
    journey = BaseJourney(MagicMock())
    journey._merge_incoming_defaults_and_params()
    assert journey._incoming_test_parameters["tags"] == {}


def test_set_test_parameters():
    journey = BaseJourney(MagicMock())
    journey.defaults = {"foo1": "bar", "foo2": "bar2"}
    journey.replace_incoming_scenario_args({"foo2": "bar3", "foo3": "bar4"})
    journey._merge_incoming_defaults_and_params()
    assert journey._incoming_test_parameters == {
        "foo1": "bar",
        "foo2": "bar3",
        "foo3": "bar4",
    }


def test_set_test_parameters_with_thresholds_and_tags():
    BaseJourney.replace_incoming_scenario_args(
        {
            "thresholds": {
                "asdf1": {"type": "get", "limit": 1},
                "asdf2": {"type": "post", "limit": 2, "percentile": 0.8},
            },
            "tags": {"foo": "bar"},
        }
    )
    journey = BaseJourney(MagicMock())
    journey.on_start()
    journey._set_thresholds()
    assert journey.environment.stats.trends["asdf1"] == {
        "thresholds": [
            {
                "less_than_in_ms": 1,
                "actual_value_in_ms": None,
                "percentile": GrasshopperConstants.THRESHOLD_PERCENTILE_DEFAULT,
                "succeeded": None,
                "http_method": "GET",
            },
        ],
        "tags": {"foo": "bar"},
    }
    assert journey.environment.stats.trends["asdf2"] == {
        "thresholds": [
            {
                "less_than_in_ms": 2,
                "actual_value_in_ms": None,
                "percentile": 0.8,
                "succeeded": None,
                "http_method": "POST",
            },
        ],
        "tags": {"foo": "bar"},
    }


def test_verify_thresholds_collection_shape_successful():
    journey = BaseJourney(MagicMock())
    valid_thresholds_collection = {
        "asdf1": {"type": "get", "limit": 1},
        "asdf2": {"type": "post", "limit": 2, "percentile": 0.8},
    }
    assert journey._verify_thresholds_collection_shape(valid_thresholds_collection)


def test_verify_thresholds_collection_shape_invalid_limit(caplog):
    journey = BaseJourney(MagicMock())
    invalid_thresholds_collection_limit = {
        "asdf1": {"type": "get", "limit": "invalid_limit"},
        "asdf2": {"type": "post", "limit": 2, "percentile": 0.8},
    }
    with caplog.at_level(logging.WARNING):
        is_valid = journey._verify_thresholds_collection_shape(
            invalid_thresholds_collection_limit
        )
    assert not is_valid
    assert "limit" in caplog.text


def test_verify_thresholds_collection_shape_invalid_type(caplog):
    journey = BaseJourney(MagicMock())
    invalid_thresholds_collection_type = {
        "asdf1": {"type": "invalid_type", "limit": 1},
        "asdf2": {"type": "post", "limit": 2, "percentile": 0.8},
    }
    with caplog.at_level(logging.WARNING):
        is_valid = journey._verify_thresholds_collection_shape(
            invalid_thresholds_collection_type
        )
    assert not is_valid
    assert "type `INVALID_TYPE` is invalid" in caplog.text


def test_verify_thresholds_collection_shape_invalid_shape(caplog):
    journey = BaseJourney(MagicMock())
    invalid_thresholds_collection = []
    with caplog.at_level(logging.WARNING):
        is_valid = journey._verify_thresholds_collection_shape(
            invalid_thresholds_collection
        )
    assert not is_valid
    assert "mapping" in caplog.text


# Tests for the new context() method
def test_context_with_no_trace_headers():
    """Test context() method when no trace headers are stored."""
    journey = BaseJourney(MagicMock())

    result = journey.context()

    # Should return all trace header keys with empty string values
    expected = {
        "trace_id": "",
        "request_id": "",
        "trifacta_request_id": "",
        "ayx_request_id": "",
    }
    assert result == expected


def test_context_with_stored_trace_headers():
    """Test context() method when trace headers are stored."""
    journey = BaseJourney(MagicMock())

    # Store some trace headers (using the same keys as get_trace_headers returns)
    journey._trace_headers = {
        "trace_id": "123456",
        "request_id": "req-789",
        "ayx_request_id": "ayx-123",
    }

    result = journey.context()

    expected = {
        "trace_id": "123456",
        "request_id": "req-789",
        "trifacta_request_id": "",  # Not stored, defaults to empty
        "ayx_request_id": "ayx-123",
    }
    assert result == expected


def test_context_with_none_trace_headers():
    """Test context() method when _trace_headers is None."""
    journey = BaseJourney(MagicMock())
    journey._trace_headers = None

    result = journey.context()

    # Should return all trace header keys with empty string values
    expected = {
        "trace_id": "",
        "request_id": "",
        "trifacta_request_id": "",
        "ayx_request_id": "",
    }
    assert result == expected


# Tests for the new capture_trace_headers() method
@patch("grasshopper.lib.journeys.base_journey.get_trace_headers")
def test_capture_trace_headers_success(mock_get_trace_headers):
    """Test capture_trace_headers() method when trace headers are found."""
    journey = BaseJourney(MagicMock())
    mock_response = MagicMock()

    expected_headers = {
        "trace_id": "123456",
        "request_id": "req-789",
        "trifacta_request_id": "trifacta-456",
        "ayx_request_id": "ayx-123",
    }
    mock_get_trace_headers.return_value = expected_headers

    result = journey.capture_trace_headers(mock_response)

    assert result == expected_headers
    assert journey._trace_headers == expected_headers
    mock_get_trace_headers.assert_called_once_with(mock_response)


@patch("grasshopper.lib.journeys.base_journey.get_trace_headers")
def test_capture_trace_headers_no_headers_found(mock_get_trace_headers, caplog):
    """Test capture_trace_headers() method when no trace headers are found."""
    journey = BaseJourney(MagicMock())
    mock_response = MagicMock()

    mock_get_trace_headers.return_value = None

    with caplog.at_level(logging.WARNING):
        result = journey.capture_trace_headers(mock_response)

    assert result is None
    assert "No trace headers found in response" in caplog.text
    mock_get_trace_headers.assert_called_once_with(mock_response)


@patch("grasshopper.lib.journeys.base_journey.get_trace_headers")
def test_capture_trace_headers_empty_headers(mock_get_trace_headers, caplog):
    """Test capture_trace_headers() method when empty headers are returned."""
    journey = BaseJourney(MagicMock())
    mock_response = MagicMock()

    mock_get_trace_headers.return_value = {}

    with caplog.at_level(logging.WARNING):
        result = journey.capture_trace_headers(mock_response)

    assert result is None
    assert "No trace headers found in response" in caplog.text
    mock_get_trace_headers.assert_called_once_with(mock_response)


@patch("grasshopper.lib.journeys.base_journey.get_trace_headers")
def test_capture_trace_headers_logs_captured_headers(mock_get_trace_headers, caplog):
    """Test capture_trace_headers() method logs captured headers."""
    journey = BaseJourney(MagicMock())
    mock_response = MagicMock()

    expected_headers = {
        "trace_id": "123456",
        "request_id": "req-789",
    }
    mock_get_trace_headers.return_value = expected_headers

    with caplog.at_level(logging.INFO):
        journey.capture_trace_headers(mock_response)

    assert f"Captured trace headers: {expected_headers}" in caplog.text


# Tests for the new scenario_args property
def test_scenario_args_property():
    """Test scenario_args property returns _test_parameters."""
    journey = BaseJourney(MagicMock())

    # Set up test parameters
    test_params = {
        "param1": "value1",
        "param2": "value2",
        "thresholds": {"test": {"type": "get", "limit": 100}},
    }
    journey._test_parameters = test_params

    result = journey.scenario_args

    assert result == test_params
    assert result is journey._test_parameters  # Should be the same object


def test_scenario_args_property_when_none():
    """Test scenario_args property when _test_parameters is not set."""
    journey = BaseJourney(MagicMock())

    # _test_parameters should not be set initially
    with pytest.raises(AttributeError):
        _ = journey.scenario_args


def test_scenario_args_property_after_on_start():
    """Test scenario_args property after on_start() has been called."""
    journey = BaseJourney(MagicMock())

    # Set up some scenario args
    BaseJourney.replace_incoming_scenario_args(
        {
            "param1": "value1",
            "target_url": "http://example.com",
            "tags": {"env": "test"},
        }
    )

    journey.on_start()

    result = journey.scenario_args

    assert "param1" in result
    assert result["param1"] == "value1"
    assert "target_url" in result
    assert result["target_url"] == "http://example.com"
    assert "tags" in result
    assert result["tags"]["env"] == "test"


# Integration test for all three new methods working together
@patch("grasshopper.lib.journeys.base_journey.get_trace_headers")
def test_integration_capture_and_context(mock_get_trace_headers):
    """Test integration of capture_trace_headers() and context() methods."""
    journey = BaseJourney(MagicMock())
    mock_response = MagicMock()

    # Set up trace headers
    trace_headers = {
        "trace_id": "trace-123",
        "request_id": "request-456",
    }
    mock_get_trace_headers.return_value = trace_headers

    # Capture the headers
    captured = journey.capture_trace_headers(mock_response)

    # Verify captured headers
    assert captured == trace_headers

    # Verify context returns the captured headers with defaults
    context = journey.context()
    expected_context = {
        "trace_id": "trace-123",
        "request_id": "request-456",
        "trifacta_request_id": "",  # Default empty
        "ayx_request_id": "",  # Default empty
    }
    assert context == expected_context
