import os
from unittest.mock import MagicMock, patch

from grasshopper.lib.fixtures import _get_tagged_scenarios


def test_get_tagged_scenarios_happy():
    config_mock = MagicMock()
    config_mock.getoption = lambda a: "asdf"
    raw_yaml_dict = {
        "scenario1": {"tags": ["asdf"]},
        "scenario2": {"tags": ["foo"]},
    }
    tagged_scenarios = _get_tagged_scenarios(raw_yaml_dict, config_mock, fspath="asdf")
    assert tagged_scenarios == {"scenario1": {"tags": ["asdf", "scenario1"]}}


@patch.dict(os.environ, {"TAGS": "foo"}, clear=True)
def test_get_tagged_scenarios_happy_env_var():
    config_mock = MagicMock()
    config_mock.getoption = lambda a: None
    raw_yaml_dict = {
        "scenario1": {"tags": ["asdf"]},
        "scenario2": {"tags": ["foo"]},
    }
    tagged_scenarios = _get_tagged_scenarios(raw_yaml_dict, config_mock, fspath="asdf")
    assert tagged_scenarios == {"scenario2": {"tags": ["foo", "scenario2"]}}


def test_get_tagged_scenarios_no_tags_supplied(caplog):
    config_mock = MagicMock()
    config_mock.getoption = lambda a: None
    raw_yaml_dict = {
        "scenario1": {"tags": ["asdf"]},
        "scenario2": {"tags": ["foo"]},
    }
    tagged_scenarios = _get_tagged_scenarios(raw_yaml_dict, config_mock, fspath="asdf")
    expected = {"scenario1": {"tags": ["asdf"]}, "scenario2": {"tags": ["foo"]}}
    assert tagged_scenarios == expected
    assert "ALL scenarios in asdf will be run!" in caplog.text
