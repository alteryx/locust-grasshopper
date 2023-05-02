from unittest.mock import MagicMock

import pytest

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
                "asdf1":
                    {
                        "type": "get",
                        "limit": 1
                    },
                "asdf2":
                    {
                        "type": "post",
                        "limit": 2,
                        "percentile": 0.8
                    }
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
                "percentile": 0.9,
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


def test_verify_thresholds_shape_successful():
    journey = BaseJourney(MagicMock())
    valid_thresholds_shape = {
        "asdf1":
            {
                "type": "get",
                "limit": 1
            },
        "asdf2":
            {
                "type": "post",
                "limit": 2,
                "percentile": 0.8
            }
    }
    assert journey._verify_thresholds_shape(valid_thresholds_shape)


def test_verify_thresholds_shape_invalid_limit():
    journey = BaseJourney(MagicMock())
    invalid_thresholds_shape_limit = {
        "asdf1":
            {
                "type": "get",
                "limit": "invalid_limit"
            },
        "asdf2":
            {
                "type": "post",
                "limit": 2,
                "percentile": 0.8
            }
    }
    assert not journey._verify_thresholds_shape(invalid_thresholds_shape_limit)


def test_verify_thresholds_shape_invalid_type():
    journey = BaseJourney(MagicMock())
    invalid_thresholds_shape_type = {
        "asdf1":
            {
                "type": "invalid_type",
                "limit": 1
            },
        "asdf2":
            {
                "type": "post",
                "limit": 2,
                "percentile": 0.8
            }
    }
    assert not journey._verify_thresholds_shape(invalid_thresholds_shape_type)


def test_extract_trend_name_is_invalid_shape():
    journey = BaseJourney(MagicMock())
    invalid_thresholds_shape = []
    assert not journey._verify_thresholds_shape(invalid_thresholds_shape)
