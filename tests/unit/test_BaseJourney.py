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
            "thresholds": {"{POST}asdf": "1", "{GET}asdf": "2"},
            "tags": {"foo": "bar"},
        }
    )
    journey = BaseJourney(MagicMock())
    journey.on_start()
    journey._set_thresholds()
    assert journey.environment.stats.trends["asdf"] == {
        "thresholds": [
            {
                "less_than_in_ms": "1",
                "actual_value_in_ms": None,
                "percentile": 0.8,
                "succeeded": None,
                "http_method": "POST",
            },
            {
                "less_than_in_ms": "2",
                "actual_value_in_ms": None,
                "percentile": 0.8,
                "succeeded": None,
                "http_method": "GET",
            },
        ],
        "tags": {"foo": "bar"},
    }


def test_extract_trend_name_successful():
    journey = BaseJourney(MagicMock())
    assert journey._extract_trend_name("{GET}asdf") == ("asdf", "GET")


def test_extract_trend_name_is_invalid():
    journey = BaseJourney(MagicMock())
    with pytest.raises(ValueError):
        journey._extract_trend_name("asdf")
