import logging
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
                "asdf1": {"type": "get", "limit": 1},
                "asdf2": {"type": "post", "limit": 2, "percentile": 0.8},
            },
            "tags": {"foo": "bar"},
        }
    )


def test_on_start_raises_type_error_when_no_host_or_target_url():
    """
    Test that on_start raises TypeError if neither target_url nor host is set.
    """
    BaseJourney.replace_incoming_scenario_args({})
    journey = BaseJourney(MagicMock())
    journey.environment = MagicMock()
    journey.environment.host = ""
    journey.host = ""
    with pytest.raises(TypeError, match="Expected a non-empty string for URL"):
        journey.on_start()


def test_on_start_uses_host_when_target_url_missing():
    """
    Test that on_start uses the class host if target_url is missing.
    """
    BaseJourney.replace_incoming_scenario_args({})
    journey = BaseJourney(MagicMock())
    journey.environment = MagicMock()
    journey.host = "http://myhost.com/"
    journey.environment.host = ""
    journey.on_start()
    assert journey.environment.host == "http://myhost.com/"


def test_on_start_uses_target_url_when_present():
    """
    Test that on_start uses target_url from scenario_args if present.
    """
    BaseJourney.replace_incoming_scenario_args(
        {"target_url": "http://mytarget_url.com/"}
    )
    journey = BaseJourney(MagicMock())
    journey.environment = MagicMock()
    journey.host = "http://myhost.com/"
    journey.environment.host = ""
    journey.on_start()
    assert journey.environment.host == "http://mytarget_url.com/"


def test_update_tags_merges_tags():
    """
    Test that update_tags merges new tags into self.tags.
    """
    journey = BaseJourney(MagicMock())
    journey.tags = {"foo": "bar"}
    journey.update_tags({"baz": "qux"})
    assert journey.tags == {"foo": "bar", "baz": "qux"}


def test_merge_incoming_scenario_args_merges_with_lower_precedence():
    """
    Test that merge_incoming_scenario_args merges lower precedence args.
    """
    BaseJourney.replace_incoming_scenario_args({"a": 1})
    BaseJourney.merge_incoming_scenario_args({"a": 0, "b": 2})
    assert BaseJourney._incoming_test_parameters == {"a": 1, "b": 2}


def test_reset_class_attributes_resets_all():
    """
    Test that reset_class_attributes resets all class-level attributes.
    """
    BaseJourney._incoming_test_parameters = {"foo": "bar"}
    BaseJourney.defaults = {"thresholds": {"x": 1}, "tags": {"y": 2}}
    BaseJourney.host = "something"
    BaseJourney.abstract = False
    BaseJourney.base_torn_down = True
    BaseJourney.VUS_DICT = {1: "something"}
    BaseJourney.reset_class_attributes()
    assert BaseJourney._incoming_test_parameters == {}
    assert BaseJourney.defaults == {"thresholds": {}, "tags": {}}
    assert BaseJourney.host == ""
    assert BaseJourney.abstract is True
    assert BaseJourney.base_torn_down is False
    assert BaseJourney.VUS_DICT == {}


def test_get_journey_object_given_vu_number_returns_correct_instance():
    """
    Test that get_journey_object_given_vu_number returns the correct journey instance.
    """
    BaseJourney.reset_class_attributes()
    journey = BaseJourney(MagicMock())
    BaseJourney.VUS_DICT[5] = journey
    assert BaseJourney.get_journey_object_given_vu_number(5) is journey
    assert BaseJourney.get_journey_object_given_vu_number(99) is None


def test__verify_thresholds_collection_shape_missing_type_and_limit(caplog):
    journey = BaseJourney(MagicMock())
    invalid = {"trend": {"percentile": 0.9}}
    with caplog.at_level(logging.WARNING):
        assert not journey._verify_thresholds_collection_shape(invalid)
    assert "must have `type`and `limit` fields defined" in caplog.text


def test__verify_thresholds_collection_shape_multiple_invalids(caplog):
    journey = BaseJourney(MagicMock())
    invalid = {
        "trend1": {"type": None, "limit": None},
        "trend2": {"type": "get", "limit": "not_a_number"},
        "trend3": {"type": "invalid", "limit": 1},
    }
    with caplog.at_level(logging.WARNING):
        assert not journey._verify_thresholds_collection_shape(invalid)
    assert (
        "must have `type`and `limit` fields defined" in caplog.text
        or "is invalid. Must be one of" in caplog.text
        or "Must be numeric" in caplog.text
    )


def test_teardown_sets_base_torn_down_and_clears_vus(monkeypatch):
    journey = BaseJourney(MagicMock())
    journey.environment = MagicMock()
    journey.environment.runner = MagicMock()
    BaseJourney.VUS_DICT = {1: journey}
    monkeypatch.setattr("gevent.sleep", lambda x: None)
    journey.teardown()
    assert journey.base_torn_down is True
    assert BaseJourney.VUS_DICT == {}
    journey.environment.runner.quit.assert_called_once()


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


def test_normalize_url_trailing_slash_and_space():
    assert (
        BaseJourney.normalize_url("http://mytarget_url.com/ ")
        == "http://mytarget_url.com/"
    )


def test_normalize_url_raises_type_error_on_non_string():
    with pytest.raises(TypeError, match="Expected a non-empty string for URL"):
        BaseJourney.normalize_url(None)
    with pytest.raises(TypeError, match="Expected a non-empty string for URL"):
        BaseJourney.normalize_url(123)
    with pytest.raises(TypeError, match="Expected a non-empty string for URL"):
        BaseJourney.normalize_url("")


def test_normalize_url_no_trailing_slash():
    assert (
        BaseJourney.normalize_url("http://mytarget_url.com")
        == "http://mytarget_url.com/"
    )
