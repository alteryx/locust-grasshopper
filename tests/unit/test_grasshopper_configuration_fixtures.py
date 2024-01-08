import os
from pathlib import Path
from unittest.mock import patch

import pytest
from assertpy import assert_that

# Alteryx Packages
# alias to make patches easier to read
from grasshopper.lib.configuration.gh_configuration import (  # noqa: N817
    ConfigurationConstants as CC,
)
from grasshopper.lib.configuration.gh_configuration import GHConfiguration


@pytest.fixture
def expected_global_defaults():
    defaults = {
        "slack_report_failures_only": False,
        "shape": "Default",
        "users": 1.0,
        "runtime": 120.0,
        "spawn_rate": 1.0,
        "scenario_delay": 0.0,
        "cleanup_s3": True,
        "slack": False,
        "influx": False,
        "report_portal": False,
        "rp_launch_name": "Grasshopper Performance Test Run | Launch name unknown",
        "rp_launch": "Grasshopper Performance Test Run | Launch name unknown",
    }
    return defaults


def test__grasshopper_scenario_args(grasshopper_scenario_args):
    # this fixture should always return {} now, but not removed in order to support
    # backwards compatibility
    assert_that(grasshopper_scenario_args).is_instance_of(GHConfiguration)
    assert_that(grasshopper_scenario_args).is_equal_to({})


def test__grasshopper_args(complete_configuration, grasshopper_args):
    # grasshopper_args fixture should just match the complete_configuration fixture
    # now, again kept around for backwards compatibility
    assert_that(grasshopper_args).is_instance_of(GHConfiguration)
    assert_that(grasshopper_args).is_equal_to(complete_configuration)


def test__global_defaults(expected_global_defaults, global_defaults):
    assert_that(global_defaults).is_instance_of(GHConfiguration)
    assert_that(global_defaults).is_equal_to(expected_global_defaults)


@patch.dict(
    CC.COMPLETE_ATTRS,
    {
        "attr1": {
            "opts": ["--attr1"],
            "attrs": {
                "action": "store",
                "help": "Attr1",
            },
        }
    },
    clear=True,
)
def test__global_defaults_no_defaults_in_attrs(pytester):
    """Test fixture doesn't raise an error if COMPLETE_ATTRS does not have any attrs
    with defaults defined."""

    # create a temporary conftest.py file
    pytester.makeconftest(
        """
        import pytest

        # import the fixture we want to test
        from grasshopper.lib.fixtures import global_defaults

    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(global_defaults):
            assert_that(global_defaults).is_instance_of(GHConfiguration)
            assert_that(global_defaults).is_equal_to(GHConfiguration())
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


@patch.dict(CC.COMPLETE_ATTRS, clear=True)
def test__global_defaults_empty_attrs(pytester):
    """Test fixture doesn't raise an error if COMPLETE_ATTRS is empty."""

    # create a temporary conftest.py file
    pytester.makeconftest(
        """
        import pytest

        # import the fixture we want to test
        from grasshopper.lib.fixtures import global_defaults

    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(global_defaults):
            assert_that(global_defaults).is_instance_of(GHConfiguration)
            assert_that(global_defaults).is_equal_to({})
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__grasshopper_config_file_args(pytester):
    """Test fixture loads a configuration file correctly."""
    # calculate the path before going into the other pytest context
    mock_config_file_path = (
        Path(__file__).parent / Path("../fixture_testing_data") / "mock_basic.config"
    )

    # create a temporary conftest.py file
    pytester.makeconftest(
        f"""
        import pytest

        # patch the fixture used to supply the path to the config file
        @pytest.fixture(scope="session")
        def grasshopper_config_file_path():
            return '{mock_config_file_path}'
        """
        + """
        @pytest.fixture
        def expected_config_args():
            args = {'influx': True,
                    'users': 1.0,
                    'spawn_rate': 1.0,
                    'runtime': 600,
                    'flow_name': 'POC flow',
                    'recipe_name': 'Untitled recipe',
                    'engine': 'photon'}
            return args

        # import the fixture we want to test
        from grasshopper.lib.fixtures import grasshopper_config_file_args

    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(grasshopper_config_file_args,
                expected_config_args):
            assert_that(grasshopper_config_file_args).is_instance_of(GHConfiguration)
            assert_that(grasshopper_config_file_args).is_equal_to(expected_config_args)
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__grasshopper_config_file_args_missing_section(pytester):
    """Test fixture does not error on a missing section."""
    # calculate the path before going into the other pytest context
    mock_config_file_path = (
        Path(__file__).parent
        / Path("../fixture_testing_data")
        / "mock_missing_section.config"
    )

    # create a temporary conftest.py file
    pytester.makeconftest(
        f"""
        import pytest

        # patch the fixture used to supply the path to the config file
        @pytest.fixture(scope="session")
        def grasshopper_config_file_path():
            return '{mock_config_file_path}'
        """
        + """
        @pytest.fixture
        def expected_config_args():
            args = {'influx': True,
                    'flow_name': 'POC flow',
                    'recipe_name': 'Untitled recipe',
                    'engine': 'photon'}
            return args

        # import the fixture we want to test
        from grasshopper.lib.fixtures import grasshopper_config_file_args

    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(grasshopper_config_file_args,
                expected_config_args):
            assert_that(grasshopper_config_file_args).is_instance_of(GHConfiguration)
            assert_that(grasshopper_config_file_args).is_equal_to(expected_config_args)
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__grasshopper_config_file_not_found(pytester):
    """Test fixture return empty config if the file is not found."""
    # calculate the path before going into the other pytest context
    mock_config_file_path = "bogus_path"

    # create a temporary conftest.py file
    pytester.makeconftest(
        f"""
        import pytest

        # patch the fixture used to supply the path to the config file
        @pytest.fixture(scope="session")
        def grasshopper_config_file_path():
            return '{mock_config_file_path}'
        """
        + """
        @pytest.fixture
        def expected_config_args():
            args = {}
            return args

        # import the fixture we want to test
        from grasshopper.lib.fixtures import grasshopper_config_file_args

    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(grasshopper_config_file_args,
                expected_config_args):
            assert_that(grasshopper_config_file_args).is_instance_of(GHConfiguration)
            assert_that(grasshopper_config_file_args).is_equal_to(expected_config_args)
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__grasshopper_config_file_invalid_yaml(pytester):
    """Test fixture returns an empty config if the file is not valid yaml."""
    # calculate the path before going into the other pytest context
    mock_config_file_path = (
        Path(__file__).parent
        / Path("../fixture_testing_data")
        / "mock_invalid_yaml.config"
    )

    # create a temporary conftest.py file
    pytester.makeconftest(
        f"""
        import pytest

        # patch the fixture used to supply the path to the config file
        @pytest.fixture(scope="session")
        def grasshopper_config_file_path():
            return '{mock_config_file_path}'
        """
        + """
        @pytest.fixture
        def expected_config_args():
            args = {}
            return args

        # import the fixture we want to test
        from grasshopper.lib.fixtures import grasshopper_config_file_args

    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(grasshopper_config_file_args,
                expected_config_args):
            assert_that(grasshopper_config_file_args).is_instance_of(GHConfiguration)
            assert_that(grasshopper_config_file_args).is_equal_to(expected_config_args)
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__grasshopper_config_file_empty_yaml(pytester):
    """Test fixture does not error on empty yaml file."""
    # calculate the path before going into the other pytest context
    mock_config_file_path = (
        Path(__file__).parent
        / Path("../fixture_testing_data")
        / "mock_empty_yaml.config"
    )

    # create a temporary conftest.py file
    pytester.makeconftest(
        f"""
        import pytest

        # patch the fixture used to supply the path to the config file
        @pytest.fixture(scope="session")
        def grasshopper_config_file_path():
            return '{mock_config_file_path}'
        """
        + """
        @pytest.fixture
        def expected_config_args():
            args = {}
            return args

        # import the fixture we want to test
        from grasshopper.lib.fixtures import grasshopper_config_file_args

    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(grasshopper_config_file_args,
                expected_config_args):
            assert_that(grasshopper_config_file_args).is_instance_of(GHConfiguration)
            assert_that(grasshopper_config_file_args).is_equal_to(expected_config_args)
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__grasshopper_config_file_extra_section(pytester):
    """Test fixture ignores any extra sections in the yaml file."""
    # calculate the path before going into the other pytest context
    mock_config_file_path = (
        Path(__file__).parent
        / Path("../fixture_testing_data")
        / "mock_extra_section.config"
    )

    # create a temporary conftest.py file
    pytester.makeconftest(
        f"""
        import pytest

        # patch the fixture used to supply the path to the config file
        @pytest.fixture(scope="session")
        def grasshopper_config_file_path():
            return '{mock_config_file_path}'
        """
        + """
        @pytest.fixture
        def expected_config_args():
            args = {'influx': True,
                    'flow_name': 'POC flow',
                    'recipe_name': 'Untitled recipe',
                    'engine': 'photon'}
            return args

        # import the fixture we want to test
        from grasshopper.lib.fixtures import grasshopper_config_file_args

    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(grasshopper_config_file_args,
                expected_config_args):
            assert_that(grasshopper_config_file_args).is_instance_of(GHConfiguration)
            assert_that(grasshopper_config_file_args).is_equal_to(expected_config_args)
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__env_var_prefix_key(env_var_prefix_key):
    """Validate default value is supplied for prefix."""
    assert_that(env_var_prefix_key).is_equal_to("GH_")


def test__env_var_prefix_key_with_diff_prefix(pytester):
    """Test fixture uses alternate definition for prefix when supplied."""

    # create a temporary conftest.py file
    pytester.makeconftest(
        """
        import pytest

        # patch the fixture used to supply the path to the config file
        @pytest.fixture(scope="session")
        def configuration_prefix_key():
            return 'MY_'

        # import the fixture we want to test
        from grasshopper.lib.fixtures import env_var_prefix_key

    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(env_var_prefix_key):
            assert_that(env_var_prefix_key).is_equal_to('MY_')
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__extra_env_var_keys(extra_env_var_keys):
    """Validate that fixture returns default for extra keys."""
    assert_that(extra_env_var_keys).is_equal_to([])


def test__extra_env_var_keys_defined(pytester):
    """Test fixture uses alternate definition for env var keys if supplied."""

    # create a temporary conftest.py file
    pytester.makeconftest(
        """
        import pytest

        # patch the fixture that optionally supplies extra keys
        @pytest.fixture(scope="session")
        def configuration_extra_env_var_keys():
            return ["ENV1", "ENV2"]

        # import the fixture we want to test
        from grasshopper.lib.fixtures import extra_env_var_keys

    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(extra_env_var_keys):
            assert_that(extra_env_var_keys).is_equal_to(['ENV1', 'ENV2'])
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


@patch.dict(os.environ, {"INFLUX_HOST": "1.1.1.1", "RUNTIME": "10"})
def test__env_var_args_happy(pytester):
    """Test fixture loads values correctly from the env vars."""

    # create a temporary conftest.py file
    pytester.makeconftest(
        """
        import pytest
        import os

        # import the fixture we want to test
        from grasshopper.lib.fixtures import env_var_args

    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(env_var_args):
            assert_that(env_var_args).is_instance_of(GHConfiguration)
            assert_that(env_var_args).is_equal_to({"influx_host": "1.1.1.1",
                "runtime": "10"})
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


@patch.dict(os.environ, clear=True)
def test__env_var_args_no_matches(pytester):
    """Test fixture return empty config if there are no matches in env vars."""

    # create a temporary conftest.py file
    pytester.makeconftest(
        """
        import pytest
        import os

        # import the fixture we want to test
        from grasshopper.lib.fixtures import env_var_args

    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(env_var_args):
            assert_that(env_var_args).is_instance_of(GHConfiguration)
            assert_that(env_var_args).is_equal_to({})
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


@patch.dict(
    os.environ,
    {
        "MY_UNIT_TEST_VAR": "some value",
        "UNIT_TEST_EXTRA": "some other value",
        "USERS": "100",
        "INFLUX_HOST": "1.1.1.1",
        "MY_": "key is testing load will skip over any env var names it can't resolve",
    },
    clear=True,
)
def test__env_var_args_extra_sources(pytester):
    """Test fixture loads correctly from extra sources, namely keys that
    start with the specified prefix and pulling extra keys from the env vars.

    Covers:
    + case where an env var with the prefix produces a key that is empty, should skip
    that value but proceed to load all other variables
    + a mix of sources for env vars - vars using the prefix, vars that have one of the
    extra keys, vars that match the list of configuration attrs

    """

    # create a temporary conftest.py file
    pytester.makeconftest(
        """
        import pytest
        import os

        # patch the fixture that optionally supplies extra keys
        @pytest.fixture(scope="session")
        def configuration_extra_env_var_keys():
            return ["UNIT_TEST_EXTRA"]

        # patch the fixture used to supply the path to the config file
        @pytest.fixture(scope="session")
        def env_var_prefix_key():
            return 'MY_'

        # import the fixture we want to test
        from grasshopper.lib.fixtures import env_var_args
    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(env_var_args):
            assert_that(env_var_args).is_instance_of(GHConfiguration)
            assert_that(env_var_args).contains_entry({"unit_test_var": "some value"})
            assert_that(env_var_args).contains_entry(
                {"unit_test_extra": "some other value"})
            assert_that(env_var_args).contains_entry({"users": "100"})
            assert_that(env_var_args).contains_entry({"influx_host": "1.1.1.1"})
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__cmdln_args_happy(pytester):
    """Test fixture loads correctly."""

    pytester.makeconftest(
        """
        import pytest
        import sys
        from unittest.mock import MagicMock
        from tests.unit.conftest import MockConfig

        @pytest.fixture(scope="session")
        def request_config():
            mock = MockConfig({"--users": 42, "--spawn_rate":.3})
            return mock

        # import the fixture we want to test
        from grasshopper.lib.fixtures import cmdln_args
    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(cmdln_args):
            assert_that(cmdln_args).is_equal_to({"users": 42, "spawn_rate":.3})
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__cmdln_args_empty_cmdln(pytester):
    """Test fixture loads correctly if there are not command line args supplied."""

    pytester.makeconftest(
        """
        import pytest
        import sys
        from unittest.mock import MagicMock
        from tests.unit.conftest import MockConfig

        @pytest.fixture(scope="session")
        def request_config():
            mock = MockConfig()
            return mock

        # import the fixture we want to test
        from grasshopper.lib.fixtures import cmdln_args
    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(cmdln_args):
            assert_that(cmdln_args).is_equal_to({})
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__cmdln_args_extra_args_coming_from_cmdln(pytester):
    """Test fixture loads correctly if there are other args in the collection, such
    as pytest args or custom args that a consumer might add in."""

    pytester.makeconftest(
        """
        import pytest
        import sys
        from unittest.mock import MagicMock
        from tests.unit.conftest import MockConfig

        @pytest.fixture(scope="session")
        def request_config():
            mock = MockConfig({"--users": 42, "--log_cli_level": "debug"})
            return mock

        # import the fixture we want to test
        from grasshopper.lib.fixtures import cmdln_args
    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(cmdln_args):
            assert_that(cmdln_args).is_equal_to({"users": 42})
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__pre_processed_args_happy(pytester):
    """Test fixture loads correctly."""

    pytester.makeconftest(
        """
        import pytest
        import sys

        from grasshopper.lib.configuration.gh_configuration import GHConfiguration

        @pytest.fixture(scope="session")
        def global_defaults():
            config = GHConfiguration()
            return config

        @pytest.fixture(scope="session")
        def grasshopper_config_file_args():
            config = GHConfiguration()
            return config

        @pytest.fixture(scope="session")
        def env_var_args():
            config = GHConfiguration()
            return config

        @pytest.fixture(scope="session")
        def cmdln_args():
            config = GHConfiguration({"scenario_file":"fake_scenario_file.yaml",
                                      "scenario_name": "fake_scenario_name"})
            return config


        # import the fixture we want to test
        from grasshopper.lib.fixtures import pre_processed_args
    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(pre_processed_args):
            expected = GHConfiguration({"scenario_file":"fake_scenario_file.yaml",
                        "scenario_name": "fake_scenario_name"})
            assert_that(pre_processed_args).is_instance_of(GHConfiguration)
            assert_that(pre_processed_args).is_equal_to(expected)
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__pre_processed_args_empty(pytester):
    """Test fixture returns an empty config if the pre-process args are not
    specified."""

    pytester.makeconftest(
        """
        import pytest
        import sys

        from grasshopper.lib.configuration.gh_configuration import GHConfiguration

        @pytest.fixture(scope="session")
        def global_defaults():
            config = GHConfiguration()
            return config

        @pytest.fixture(scope="session")
        def grasshopper_config_file_args():
            config = GHConfiguration()
            return config

        @pytest.fixture(scope="session")
        def env_var_args():
            config = GHConfiguration()
            return config

        @pytest.fixture(scope="session")
        def cmdln_args():
            config = GHConfiguration({})
            return config

        # import the fixture we want to test
        from grasshopper.lib.fixtures import pre_processed_args
    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(pre_processed_args):
            assert_that(pre_processed_args).is_instance_of(GHConfiguration)
            assert_that(pre_processed_args).is_equal_to({})
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__pre_processed_args_with_precedence(pytester):
    """Test fixture loads with the correct precedence applied.

    This test also covers some other test cases:
    + should be able to handle a source that is empty, in this case global defaults
    + should be able to handle a source that has extra, unrelated keys in addition to
    the keys it is looking for (config file args)
    + should be able to handle one key coming from one source and the other key coming
    from another source

    """

    pytester.makeconftest(
        """
        import pytest
        import sys

        from grasshopper.lib.configuration.gh_configuration import GHConfiguration

        @pytest.fixture(scope="session")
        def global_defaults():
            config = GHConfiguration()
            return config

        @pytest.fixture(scope="session")
        def grasshopper_config_file_args():
            config = GHConfiguration({"scenario_file":
                "from_config_file_not_the_one.yaml"})
            return config

        @pytest.fixture(scope="session")
        def env_var_args():
            config = GHConfiguration({"scenario_file":
                "from_env_var_not_the_one.yaml",
                "scenario_name": "this_is_the_one"})
            return config

        @pytest.fixture(scope="session")
        def cmdln_args():
            config = GHConfiguration({"scenario_file":
                "from_cmdln_this_is_the_one.yaml"})
            return config

        # import the fixture we want to test
        from grasshopper.lib.fixtures import pre_processed_args
    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(pre_processed_args):
            expected = GHConfiguration({"scenario_file":
                "from_cmdln_this_is_the_one.yaml",
                "scenario_name": "this_is_the_one"
                })
            assert_that(pre_processed_args).is_instance_of(GHConfiguration)
            assert_that(pre_processed_args).is_equal_to(expected)
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__scenario_file_args_happy(pytester):
    """Test fixture loads with the correct precedence applied."""

    mock_scenario_file_path = (
        Path(__file__).parent / Path("../fixture_testing_data") / "mock_scenarios.yaml"
    )

    pytester.makeconftest(
        """
                import pytest
                pre_config = {}
        """
        + f"""
                pre_config['scenario_file'] = "{mock_scenario_file_path}"
                pre_config['scenario_name'] = "scenario1"
        """
        + """
                # patch the fixture that supplies a valid file and scenario name
                @pytest.fixture(scope="session")
                def pre_processed_args():
                    return pre_config

                # import the fixture we want to test
                from grasshopper.lib.fixtures import scenario_file_args

            """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(scenario_file_args):
            expected = GHConfiguration({"users": 1,
                                        "spawn_rate": 1,
                                        "runtime": 600,
                                        "flow_name" : 'POC flow',
                                        "recipe_name": 'Untitled recipe',
                                        "engine": 'photon',
                                        'scenario_test_file_name': 'test__journey1.py',
                                        'scenario_tags': ['smoke', 'trend'],
                                        "thresholds":
                                        '{"{CUSTOM}PX_TREND_google_home": 1000}'
                                        })
            assert_that(scenario_file_args).is_instance_of(GHConfiguration)
            assert_that(scenario_file_args).is_equal_to(expected)
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__scenario_file_args_scenario_not_in_file(pytester):
    """Test fixture returns an empty config if the scenario is not found in the file."""

    mock_scenario_file_path = (
        Path(__file__).parent / Path("../fixture_testing_data") / "mock_scenarios.yaml"
    )

    pytester.makeconftest(
        """
                import pytest
                pre_config = {}
        """
        + f"""
                pre_config['scenario_file'] = "{mock_scenario_file_path}"
                pre_config['scenario_name'] = "bogus"
        """
        + """
                # patch the fixture that supplies a valid file and scenario name
                @pytest.fixture(scope="session")
                def pre_processed_args():
                    return pre_config

                # import the fixture we want to test
                from grasshopper.lib.fixtures import scenario_file_args

            """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(scenario_file_args):
            expected = GHConfiguration()
            assert_that(scenario_file_args).is_instance_of(GHConfiguration)
            assert_that(scenario_file_args).is_equal_to(expected)
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__scenario_file_args_missing_scenario(pytester):
    """Test fixture return empty config if the scenario_name arg is missing."""

    mock_scenario_file_path = (
        Path(__file__).parent / Path("../fixture_testing_data") / "mock_scenarios.yaml"
    )

    pytester.makeconftest(
        """
                import pytest
                pre_config = {}
        """
        + f"""
                pre_config['scenario_file'] = "{mock_scenario_file_path}"
        """
        + """
                # patch the fixture that supplies a valid file and scenario name
                @pytest.fixture(scope="session")
                def pre_processed_args():
                    return pre_config

                # import the fixture we want to test
                from grasshopper.lib.fixtures import scenario_file_args

            """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(scenario_file_args):
            expected = GHConfiguration()
            assert_that(scenario_file_args).is_instance_of(GHConfiguration)
            assert_that(scenario_file_args).is_equal_to(expected)
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__scenario_file_args_file_not_found(pytester):
    """Test fixture returns an empty config if the scenario_file path is not found."""

    pytester.makeconftest(
        """
                import pytest
                pre_config = {}
                pre_config['scenario_file'] = "bogus_file.yaml"

                # patch the fixture that supplies a valid file and scenario name
                @pytest.fixture(scope="session")
                def pre_processed_args():
                    return pre_config

                # import the fixture we want to test
                from grasshopper.lib.fixtures import scenario_file_args

            """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(scenario_file_args):
            expected = GHConfiguration()
            assert_that(scenario_file_args).is_instance_of(GHConfiguration)
            assert_that(scenario_file_args).is_equal_to(expected)
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__scenario_file_args_missing_scenario_keys(pytester):
    """Test fixture loads everything present, even if scenario is 'missing' keys."""

    mock_scenario_file_path = (
        Path(__file__).parent / Path("../fixture_testing_data") / "mock_scenarios.yaml"
    )

    pytester.makeconftest(
        """
                import pytest
                pre_config = {}
        """
        + f"""
                pre_config['scenario_file'] = "{mock_scenario_file_path}"
                pre_config['scenario_name'] = "scenario2"
        """
        + """
                # patch the fixture that supplies a file and scenario name
                @pytest.fixture(scope="session")
                def pre_processed_args():
                    return pre_config

                # import the fixture we want to test
                from grasshopper.lib.fixtures import scenario_file_args

            """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(scenario_file_args):
            expected = GHConfiguration({'flow_name': 'POC flow',
                                        'recipe_name': 'Untitled recipe',
                                        'engine': 'photon',
                                        'thresholds':
                                            '{"{CUSTOM}PX_TREND_google_home": 1000}',
                                        'scenario_tags': ['smoke', 'trend']})
            assert_that(scenario_file_args).is_instance_of(GHConfiguration)
            assert_that(scenario_file_args).is_equal_to(expected)
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__merge_sources_happy(pytester):
    """Test fixture loads correctly."""

    pytester.makeconftest(
        """
        import pytest
        import sys

        from grasshopper.lib.configuration.gh_configuration import GHConfiguration

        cmd = {"key1": "CMD_the_one", "CMD": "the_one"}
        env = {"key1": "ENV_not_me",
                "key2": "ENV_the_one",
                "ENV": "the_one",
                "sparse": "ENV_the_one"}
        sce = {"key1": "SCE_not_me",
                "key2": "SCE_not_me",
                "key3": "SCE_the_one",
                "SCE": "the_one",
                "extra_key4": "SCE_the_one",
                "extra_key5": "SCE_the_one"}
        cfg = {"key1": "CFG_not_me",
                "key2": "CFG_not_me",
                "key3": "CFG_not_me",
                "key4": "CFG_the_one",
                "CFG": "the_one",
                "sparse": "CFG_not_me"}
        dft = {"key1": "DFT_not_me",
                "key2": "DFT_not_me",
                "key3": "DFT_not_me",
                "key4": "DFT_the_one",
                "key5": "DFT_the_one",
                "DFT": "the_one"}

        @pytest.fixture(scope="session")
        def expected_merge():
            expected = {'key1': 'CMD_the_one',
                        'key2': 'ENV_the_one',
                        'key3': 'SCE_the_one',
                        'key4': 'CFG_the_one',
                        'key5': 'DFT_the_one',
                        "DFT": "the_one",
                        "CFG": "the_one",
                        'SCE': 'the_one',
                        'extra_key4': 'SCE_the_one',
                        'extra_key5': 'SCE_the_one',
                        'ENV': 'the_one',
                        "sparse": "ENV_the_one",
                        'CMD': 'the_one'}

            merged = GHConfiguration(expected)
            return merged

        @pytest.fixture(scope="session")
        def global_defaults():
            config = GHConfiguration(dft)
            return config

        @pytest.fixture(scope="session")
        def grasshopper_config_file_args():
            config = GHConfiguration(cfg)
            return config

        @pytest.fixture(scope="session")
        def scenario_file_args():
            config = GHConfiguration(sce)
            return config

        @pytest.fixture(scope="session")
        def env_var_args():
            config = GHConfiguration(env)
            return config

        @pytest.fixture(scope="session")
        def cmdln_args():
            config = GHConfiguration(cmd)
            return config


        # import the fixture we want to test
        from grasshopper.lib.fixtures import merge_sources
    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(merge_sources, expected_merge):
            assert_that(merge_sources).is_instance_of(GHConfiguration)
            assert_that(merge_sources).is_equal_to(expected_merge)
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__merge_sources_empty_source(pytester):
    """Test fixture loads correctly if one of the sources is empty."""

    pytester.makeconftest(
        """
        import pytest
        import sys

        from grasshopper.lib.configuration.gh_configuration import GHConfiguration

        cmd = {"key1": "CMD_the_one", "CMD": "the_one"}
        env = {"key1": "ENV_not_me",
                "key2": "ENV_the_one",
                "ENV": "the_one",
                "sparse": "ENV_the_one"}
        sce = {}
        cfg = {"key1": "CFG_not_me",
                "key2": "CFG_not_me",
                "key4": "CFG_the_one",
                "CFG": "the_one",
                "sparse": "CFG_not_me"}
        dft = {"key1": "DFT_not_me",
                "key2": "DFT_not_me",
                "key4": "DFT_the_one",
                "key5": "DFT_the_one",
                "DFT": "the_one"}

        @pytest.fixture(scope="session")
        def expected_merge():
            expected = {'key1': 'CMD_the_one',
                        'key2': 'ENV_the_one',
                        'key4': 'CFG_the_one',
                        'key5': 'DFT_the_one',
                        "DFT": "the_one",
                        "CFG": "the_one",
                        'ENV': 'the_one',
                        "sparse": "ENV_the_one",
                        'CMD': 'the_one'}

            merged = GHConfiguration(expected)
            return merged

        @pytest.fixture(scope="session")
        def global_defaults():
            config = GHConfiguration(dft)
            return config

        @pytest.fixture(scope="session")
        def grasshopper_config_file_args():
            config = GHConfiguration(cfg)
            return config

        @pytest.fixture(scope="session")
        def scenario_file_args():
            config = GHConfiguration(sce)
            return config

        @pytest.fixture(scope="session")
        def env_var_args():
            config = GHConfiguration(env)
            return config

        @pytest.fixture(scope="session")
        def cmdln_args():
            config = GHConfiguration(cmd)
            return config


        # import the fixture we want to test
        from grasshopper.lib.fixtures import merge_sources
    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(merge_sources, expected_merge):
            assert_that(merge_sources).is_instance_of(GHConfiguration)
            assert_that(merge_sources).is_equal_to(expected_merge)
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__merge_sources_all_sources_empty(pytester):
    """Test fixture returns an empty config if all the sources are empty."""

    pytester.makeconftest(
        """
        import pytest
        import sys

        from grasshopper.lib.configuration.gh_configuration import GHConfiguration

        @pytest.fixture(scope="session")
        def global_defaults():
            config = GHConfiguration()
            return config

        @pytest.fixture(scope="session")
        def grasshopper_config_file_args():
            config = GHConfiguration()
            return config

        @pytest.fixture(scope="session")
        def scenario_file_args():
            config = GHConfiguration()
            return config

        @pytest.fixture(scope="session")
        def env_var_args():
            config = GHConfiguration()
            return config

        @pytest.fixture(scope="session")
        def cmdln_args():
            config = GHConfiguration()
            return config


        # import the fixture we want to test
        from grasshopper.lib.fixtures import merge_sources
    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(merge_sources):
            assert_that(merge_sources).is_instance_of(GHConfiguration)
            assert_that(merge_sources).is_equal_to(GHConfiguration())
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__merge_sources_invalid_source(pytester):
    """Test fixture does not raise an error if one source is invalid."""

    pytester.makeconftest(
        """
        import pytest
        import sys

        from grasshopper.lib.configuration.gh_configuration import GHConfiguration

        cmd = {"key1": "CMD_the_one", "CMD": "the_one"}
        env = {"key1": "ENV_not_me",
                "key2": "ENV_the_one",
                "ENV": "the_one",
                "sparse": "ENV_the_one"}
        sce = {"key1": "SCE_not_me",
                "key2": "SCE_not_me",
                "key3": "SCE_the_one",
                "SCE": "the_one",
                "extra_key4": "SCE_the_one",
                "extra_key5": "SCE_the_one"}
        dft = {"key1": "DFT_not_me",
                "key2": "DFT_not_me",
                "key3": "DFT_not_me",
                "key5": "DFT_the_one",
                "DFT": "the_one"}

        @pytest.fixture(scope="session")
        def expected_merge():
            expected = {'key1': 'CMD_the_one',
                        'key2': 'ENV_the_one',
                        'key3': 'SCE_the_one',
                        'key5': 'DFT_the_one',
                        "DFT": "the_one",
                        'SCE': 'the_one',
                        'extra_key4': 'SCE_the_one',
                        'extra_key5': 'SCE_the_one',
                        'ENV': 'the_one',
                        "sparse": "ENV_the_one",
                        'CMD': 'the_one'}

            merged = GHConfiguration(expected)
            return GHConfiguration(dft)

        @pytest.fixture(scope="session")
        def global_defaults():
            config = GHConfiguration(dft)
            return config

        @pytest.fixture(scope="session")
        def grasshopper_config_file_args():
            return None

        @pytest.fixture(scope="session")
        def scenario_file_args():
            config = GHConfiguration(sce)
            return config

        @pytest.fixture(scope="session")
        def env_var_args():
            config = GHConfiguration(env)
            return config

        @pytest.fixture(scope="session")
        def cmdln_args():
            config = GHConfiguration(cmd)
            return config


        # import the fixture we want to test
        from grasshopper.lib.fixtures import merge_sources
    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(merge_sources, expected_merge):
            assert_that(merge_sources).is_instance_of(GHConfiguration)
            assert_that(merge_sources).is_equal_to(expected_merge)
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__typecast_happy(pytester):
    """Test fixture applies the 'typecast' lambdas correctly.

    Covers the following test cases:
    + applying all typecast lambdas at least once
    + checks that all the values that should be typecast (per the
    ConfigurationConstants class) were actually typecast
    + that if a value is already the correct format, no errors are raised
    + extra values that don't have a typecast are passed through to the return
    configuration
    """

    pytester.makeconftest(
        """
        import pytest
        import sys

        from grasshopper.lib.configuration.gh_configuration import GHConfiguration


        @pytest.fixture(scope="session")
        def merge_sources():
            cfg_values = {"slack_report_failures_only": "false",
                            "users": "1",
                            "runtime": 180,
                            "spawn_rate": ".01",
                            "scenario_delay": "20",
                            "cleanup_s3": True,
                            "slack": "false",
                            "influx": "false",
                            "report_portal": "false",
                            "thresholds": '{"{CUSTOM}PX_TREND_google_home": 1000}',
                            "no_typecast_str": "value not typecast",
                            "no_typecast_int": 10
                            }
            config = GHConfiguration(cfg_values)
            return config

        # import the fixture we want to test
        from grasshopper.lib.fixtures import typecast
    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(typecast):
            expected_dict = {'slack_report_failures_only': False,
                            'users': 1,
                            'runtime': 180.0,
                            'spawn_rate': 0.01,
                            'scenario_delay': 20.0,
                            'cleanup_s3': True,
                            'slack': False,
                            'influx': False,
                            'report_portal': False,
                            'thresholds': {'{CUSTOM}PX_TREND_google_home': 1000},
                            'no_typecast_str': 'value not typecast',
                            'no_typecast_int': 10}

            expected = GHConfiguration(expected_dict)
            assert_that(typecast).is_instance_of(GHConfiguration)
            assert_that(typecast).is_equal_to(expected)
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__typecast_cast_fails(pytester):
    """Test fixture errors if a cast fails."""

    pytester.makeconftest(
        """
        import pytest
        import sys

        from grasshopper.lib.configuration.gh_configuration import GHConfiguration


        @pytest.fixture(scope="session")
        def merge_sources():
            cfg_values = {"runtime": "this is not a float"}
            config = GHConfiguration(cfg_values)
            return config

        # import the fixture we want to test
        from grasshopper.lib.fixtures import typecast
    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(typecast):
            # should raise a ValueError
            pass
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(errors=1)


def test__typecast_no_casting(pytester):
    """Test fixture returns incoming values if there is no typecasting that needs to
    happen."""

    pytester.makeconftest(
        """
        import pytest
        import sys

        from grasshopper.lib.configuration.gh_configuration import GHConfiguration


        @pytest.fixture(scope="session")
        def merge_sources():
            cfg_values = {"no_typecast_str": "value not typecast"}
            config = GHConfiguration(cfg_values)
            return config

        # import the fixture we want to test
        from grasshopper.lib.fixtures import typecast
    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(typecast):
            expected = GHConfiguration({"no_typecast_str": "value not typecast"})
            assert_that(typecast).is_instance_of(GHConfiguration)
            assert_that(typecast).is_equal_to(expected)
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__typecast_empty_source(pytester):
    """Test fixture return empty config if incoming args are empty."""

    pytester.makeconftest(
        """
        import pytest
        import sys

        from grasshopper.lib.configuration.gh_configuration import GHConfiguration


        @pytest.fixture(scope="session")
        def merge_sources():
            config = GHConfiguration()
            return config

        # import the fixture we want to test
        from grasshopper.lib.fixtures import typecast
    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(typecast):
            assert_that(typecast).is_instance_of(GHConfiguration)
            assert_that(typecast).is_equal_to(GHConfiguration())
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__process_shape_happy(pytester):
    """Test fixture correctly loads the shape into the config.

    Also, covers the case where a shape is overriding some values, with one key
    previously existing in the config and one key not existing.

    """

    pytester.makeconftest(
        """
        import pytest
        import sys

        from grasshopper.lib.configuration.gh_configuration import GHConfiguration


        @pytest.fixture(scope="session")
        def typecast():
            config = GHConfiguration(shape="Trend", spawn_rate=20)
            return config

        # import the fixture we want to test
        from grasshopper.lib.fixtures import process_shape
    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from grasshopper.lib.util.shapes import Trend
        from assertpy import assert_that

        def test_grasshopper_fixture(process_shape):
            assert_that(process_shape).is_instance_of(GHConfiguration)
            assert_that(process_shape).contains_entry({"shape": "Trend"},
                                                        {"users": 10},
                                                        {"spawn_rate": .1})
            assert_that(process_shape["shape_instance"]).is_instance_of(Trend)
    """
    )
    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__process_shape_existing_instance(pytester):
    """Test fixture loads correctly if shape_instance already has a value."""

    pytester.makeconftest(
        """
        import pytest
        import sys

        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from grasshopper.lib.util.shapes import Spike

        @pytest.fixture(scope="session")
        def typecast():
            config = GHConfiguration({"shape": "Spike", "shape_instance": Spike()})
            return config

        # import the fixture we want to test
        from grasshopper.lib.fixtures import process_shape
    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from grasshopper.lib.util.shapes import Spike
        from assertpy import assert_that

        def test_grasshopper_fixture(process_shape):
            assert_that(process_shape).is_instance_of(GHConfiguration)
            assert_that(process_shape).is_length(2)
            shape_instance = process_shape["shape_instance"]
            assert_that(shape_instance).is_instance_of(Spike)
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__process_shape_not_found(pytester):
    """Test fixture errors if it is unable to load the specified shape."""

    pytester.makeconftest(
        """
        import pytest
        import sys

        from grasshopper.lib.configuration.gh_configuration import GHConfiguration

        @pytest.fixture(scope="session")
        def typecast():
            config = GHConfiguration({"shape": "bogus"})
            return config

        # import the fixture we want to test
        from grasshopper.lib.fixtures import process_shape
    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from grasshopper.lib.util.shapes import Spike
        from assertpy import assert_that

        def test_grasshopper_fixture(process_shape):
            pass
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(errors=1)


def test__process_shape_overrides(pytester):
    """Test fixture correctly is merging in 'approved' overrides from the shape
    instance."""

    pytester.makeconftest(
        """
        import pytest
        import sys

        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from grasshopper.lib.util.shapes import Testingfixturesonly

        @pytest.fixture(scope="session")
        def typecast():
            config = GHConfiguration(shape="Testingfixturesonly",
                                    key_that_should_not_override="the one",
                                    some_other_key="some other value",
                                    users=100)
            return config

        # import the fixture we want to test
        from grasshopper.lib.fixtures import process_shape
    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from grasshopper.lib.util.shapes import Testingfixturesonly
        from assertpy import assert_that

        def test_grasshopper_fixture(process_shape):
            assert_that(process_shape).is_instance_of(GHConfiguration)
            assert_that(process_shape).is_length(7)
            shape_instance = process_shape["shape_instance"]
            assert_that(shape_instance).is_instance_of(Testingfixturesonly)

            # Smoke shape returns some overrides, make sure _only_ those that are
            # "approved" are put into the dictionary
            assert_that(process_shape).contains_entry({"runtime": 10})
            assert_that(process_shape).contains_entry({"users": 20})
            assert_that(process_shape).contains_entry({"spawn_rate": 0.004})
            assert_that(process_shape).contains_entry({"key_that_should_not_override":
                                                        "the one"})
            assert_that(process_shape).contains_entry({"some_other_key":
                                                        "some other value"})
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test__complete_configuration(pytester):
    """Test fixture returns incoming args, with only legacy args being translated to
    the new key name."""

    pytester.makeconftest(
        """
        import pytest
        import sys

        from grasshopper.lib.configuration.gh_configuration import GHConfiguration

        expected_global_defaults = {"slack_report_failures_only": False,
                                    "shape": "Default",
                                    "users": 1.0,
                                    "runtime": 120.0,
                                    "spawn_rate": 1.0,
                                    "scenario_delay": 0.0,
                                    "cleanup_s3": True,
                                    "slack": False,
                                    "influx": False,
                                    "report_portal": False
                                }
        @pytest.fixture(scope="session")
        def process_shape():
            config = GHConfiguration(**expected_global_defaults, influxdb="2.2.2.2")
            return config

        # import the fixture we want to test
        from grasshopper.lib.fixtures import complete_configuration
    """
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(complete_configuration):
            args = {"slack_report_failures_only": False,
                        "shape": "Default",
                        "users": 1.0,
                        "runtime": 120.0,
                        "spawn_rate": 1.0,
                        "scenario_delay": 0.0,
                        "cleanup_s3": True,
                        "slack": False,
                        "influx": False,
                        "report_portal": False,
                        "influxdb": "2.2.2.2",
                        "influx_host": "2.2.2.2"
                    }
            expected = GHConfiguration(args)
            assert_that(complete_configuration).is_instance_of(GHConfiguration)
            assert_that(complete_configuration).is_equal_to(expected)
    """
    )

    # run all tests with pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)
