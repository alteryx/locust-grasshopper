import os
from unittest.mock import patch

from grasshopper.lib.configuration.gh_configuration import (  # noqa: N817
    ConfigurationConstants as CC,
)

# Alteryx Packages
from tests.unit.conftest import (
    CONFTEST_TEMPLATE,
    PYFILE_ASSERT_EMPTY_CONFIG,
    PYFILE_ASSERT_EXPECTED_CONFIG,
    PYFILE_TEMPLATE,
    perform_fixture_test_with_optional_log_capture,
)

FIXTURE_UNDER_TEST = "env_var_args"

# Some comments on testing fixture env_var_args.
# There are fairly complete unit tests for the extra_env_var_args fixture that assert
# that _this fixture's value_ will _only_ be a list of strings or [].
# Therefore, we only need to test this fixture passing in [] (default, what you get if
# you don't patch it) and a list of strings.
# Similarly, we only need to test env_var_args receiving a non-zero length string as the
# custom prefix.
# If any of the tests here are failing, it would be worthwhile to check the results of
# `test__fixture__extra_env_var_args` and `test__fixture__env_var_prefix_key` before
# debugging here.
# Additionally, note that the expected behavior for env_var_args is lower case all keys
# _after_ matching.

# Matching some values from COMPLETE_ATTRS
FAKE_ENVIRON_SOME_MATCHING_VALUES = {"INFLUX_HOST": "1.1.1.1", "RUNTIME": "10"}

# Keys that don't match anything from COMPLETE_ATTRS
FAKE_ENVIRON_NON_MATCHING_VALUES = {
    "COMPLETELY_UNRELATED_KEY": "completely unrelated value",
    "ANOTHER_UNRELATED_KEY": "some other value",
}

# Mix of keys that match and don't match COMPLETE_ATTRS
FAKE_ENVIRON_MIX_MATCH_AND_NOT = {
    **FAKE_ENVIRON_SOME_MATCHING_VALUES,
    **FAKE_ENVIRON_NON_MATCHING_VALUES,
}

# Keys that match external sources (env_var_keys & custom prefix)
FAKE_ENVIRON_KEYS_MATCHING_OTHER_SOURCES = {
    "MY_UNIT_TEST_VAR": "testing var from extra keys set is loaded",
    "UNIT_TEST_EXTRA": "testing that extra env var args are loaded",
}

# Keys that won't resolve correctly paired with certain prefix keys
FAKE_ENVIRON_KEYS_THAT_WONT_RESOLVE = {
    "OOOPS_": "testing load will skip over any env var names it can't resolve",
}

# All different types of keys, in order to test that the fixture can load all the
# different types of sources _at the same time_ and not include irrelevant data
FAKE_ENVIRON_ALL_SOURCES_AND_NON_MATCHING_VALUES = {
    **FAKE_ENVIRON_MIX_MATCH_AND_NOT,
    **FAKE_ENVIRON_KEYS_MATCHING_OTHER_SOURCES,
    **FAKE_ENVIRON_KEYS_THAT_WONT_RESOLVE,
    "MY_": "value that should not load",
}


@patch.dict(os.environ, FAKE_ENVIRON_SOME_MATCHING_VALUES, clear=True)
def test__env_var_args__happy(pytester):
    """Fixture should load any env vars that match keys in COMPLETE_ATTRS."""

    pytester.makeconftest(
        CONFTEST_TEMPLATE.format(fixture_name=FIXTURE_UNDER_TEST, patches="")
    )
    expected_config_args = {"influx_host": "1.1.1.1", "runtime": "10"}
    pytester.makepyfile(
        PYFILE_TEMPLATE.format(
            fixture_name=FIXTURE_UNDER_TEST,
            validations=PYFILE_ASSERT_EXPECTED_CONFIG.format(
                fixture_name=FIXTURE_UNDER_TEST,
                expected=expected_config_args,
            ),
        )
    )

    perform_fixture_test_with_optional_log_capture(pytester)


@patch.dict(os.environ, FAKE_ENVIRON_NON_MATCHING_VALUES, clear=True)
def test__env_var_args__no_matches(pytester):
    """Fixture should return an empty config if there are no values that match keys
    in COMPLETE_ATTRS."""

    pytester.makeconftest(
        CONFTEST_TEMPLATE.format(fixture_name=FIXTURE_UNDER_TEST, patches="")
    )
    pytester.makepyfile(
        PYFILE_TEMPLATE.format(
            fixture_name=FIXTURE_UNDER_TEST,
            validations=PYFILE_ASSERT_EMPTY_CONFIG.format(
                fixture_name=FIXTURE_UNDER_TEST
            ),
        )
    )

    perform_fixture_test_with_optional_log_capture(pytester)


@patch.dict(os.environ, clear=True)
def test__env_var_args__environ_empty(pytester):
    """Fixture should return an empty config if environ is empty."""

    pytester.makeconftest(
        CONFTEST_TEMPLATE.format(fixture_name=FIXTURE_UNDER_TEST, patches="")
    )
    pytester.makepyfile(
        PYFILE_TEMPLATE.format(
            fixture_name=FIXTURE_UNDER_TEST,
            validations=PYFILE_ASSERT_EMPTY_CONFIG.format(
                fixture_name=FIXTURE_UNDER_TEST
            ),
        )
    )

    perform_fixture_test_with_optional_log_capture(pytester)


@patch.dict(os.environ, FAKE_ENVIRON_KEYS_MATCHING_OTHER_SOURCES, clear=True)
def test__env_var_args__matching_extra_keys(pytester):
    """Fixture should load keys that match values in extra_env_var_keys."""

    patches = """
        @pytest.fixture(scope="session")
        def extra_env_var_keys():
            return ["UNIT_TEST_EXTRA", "KEY_THAT_IS_NOT_IN_ENVIRON"]
        """
    pytester.makeconftest(
        CONFTEST_TEMPLATE.format(fixture_name=FIXTURE_UNDER_TEST, patches=patches)
    )
    expected_config_args = {
        "unit_test_extra": "testing that extra env var args are loaded"
    }
    pytester.makepyfile(
        PYFILE_TEMPLATE.format(
            fixture_name=FIXTURE_UNDER_TEST,
            validations=PYFILE_ASSERT_EXPECTED_CONFIG.format(
                fixture_name=FIXTURE_UNDER_TEST,
                expected=expected_config_args,
            ),
        )
    )

    perform_fixture_test_with_optional_log_capture(pytester)


@patch.dict(os.environ, FAKE_ENVIRON_KEYS_MATCHING_OTHER_SOURCES, clear=True)
def test__env_var_args__matching_custom_prefix(pytester):
    """Fixture should load any keys in environ that begin with the custom prefix,
    discarding the prefix portion."""

    patches = """
        @pytest.fixture(scope="session")
        def env_var_prefix_key():
            return 'MY_'
        """
    pytester.makeconftest(
        CONFTEST_TEMPLATE.format(fixture_name=FIXTURE_UNDER_TEST, patches=patches)
    )
    expected_config_args = {
        "unit_test_var": "testing var from extra keys set is loaded",
    }
    pytester.makepyfile(
        PYFILE_TEMPLATE.format(
            fixture_name=FIXTURE_UNDER_TEST,
            validations=PYFILE_ASSERT_EXPECTED_CONFIG.format(
                fixture_name=FIXTURE_UNDER_TEST,
                expected=expected_config_args,
            ),
        )
    )

    perform_fixture_test_with_optional_log_capture(pytester)


@patch.dict(os.environ, FAKE_ENVIRON_KEYS_THAT_WONT_RESOLVE, clear=True)
def test__env_var_args__skipping_keys_that_dont_resolve_correctly(pytester):
    """Fixture returns an empty config if matching key results in a invalid key.
    This can happen if, once the prefix is stripped, the key is an empty string."""

    patches = """
        @pytest.fixture(scope="session")
        def env_var_prefix_key():
            return 'OOOPS_'
        """
    pytester.makeconftest(
        CONFTEST_TEMPLATE.format(fixture_name=FIXTURE_UNDER_TEST, patches=patches)
    )
    pytester.makepyfile(
        PYFILE_TEMPLATE.format(
            fixture_name=FIXTURE_UNDER_TEST,
            validations=PYFILE_ASSERT_EMPTY_CONFIG.format(
                fixture_name=FIXTURE_UNDER_TEST
            ),
        )
    )

    perform_fixture_test_with_optional_log_capture(pytester)


@patch.dict(os.environ, FAKE_ENVIRON_ALL_SOURCES_AND_NON_MATCHING_VALUES, clear=True)
def test__env_var_args__loading_from_all_sources(pytester):
    """Fixture should load values from all different sources, and ignore anything in
    environ that doesn't match."""

    patches = """
        @pytest.fixture(scope="session")
        def env_var_prefix_key():
            return 'MY_'

        @pytest.fixture(scope="session")
        def configuration_extra_env_var_keys():
            return ["UNIT_TEST_EXTRA"]
        """
    pytester.makeconftest(
        CONFTEST_TEMPLATE.format(fixture_name=FIXTURE_UNDER_TEST, patches=patches)
    )
    expected_config_args = {
        "unit_test_var": "testing var from extra keys set is loaded",
        "unit_test_extra": "testing that extra env var args are loaded",
        "influx_host": "1.1.1.1",
        "runtime": "10",
    }
    pytester.makepyfile(
        PYFILE_TEMPLATE.format(
            fixture_name=FIXTURE_UNDER_TEST,
            validations=PYFILE_ASSERT_EXPECTED_CONFIG.format(
                fixture_name=FIXTURE_UNDER_TEST,
                expected=expected_config_args,
            ),
        )
    )

    perform_fixture_test_with_optional_log_capture(pytester)


@patch.dict(os.environ, FAKE_ENVIRON_SOME_MATCHING_VALUES, clear=True)
@patch.dict(CC.COMPLETE_ATTRS, clear=True)
def test__env_var_args__empty_attrs(pytester):
    """Fixture should return an empty config if COMPLETE_ATTRS is empty."""

    pytester.makeconftest(
        CONFTEST_TEMPLATE.format(fixture_name=FIXTURE_UNDER_TEST, patches="")
    )
    pytester.makepyfile(
        PYFILE_TEMPLATE.format(
            fixture_name=FIXTURE_UNDER_TEST,
            validations=PYFILE_ASSERT_EMPTY_CONFIG.format(
                fixture_name=FIXTURE_UNDER_TEST
            ),
        )
    )

    perform_fixture_test_with_optional_log_capture(pytester)


@patch.dict(os.environ, clear=True)
@patch.dict(CC.COMPLETE_ATTRS, clear=True)
def test__env_var_args__empty_attrs_and_empty_env_vars(pytester):
    """Fixture should return an empty config if COMPLETE_ATTRS is empty."""

    pytester.makeconftest(
        CONFTEST_TEMPLATE.format(fixture_name=FIXTURE_UNDER_TEST, patches="")
    )
    pytester.makepyfile(
        PYFILE_TEMPLATE.format(
            fixture_name=FIXTURE_UNDER_TEST,
            validations=PYFILE_ASSERT_EMPTY_CONFIG.format(
                fixture_name=FIXTURE_UNDER_TEST
            ),
        )
    )

    perform_fixture_test_with_optional_log_capture(pytester)
