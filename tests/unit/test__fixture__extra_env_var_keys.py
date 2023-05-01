import logging

from assertpy import assert_that

from tests.unit.conftest import (  # noqa: I202
    CONFTEST_TEMPLATE,
    message_was_not_logged,
    perform_fixture_test_with_optional_log_capture,
)

FIXTURE_UNDER_TEST = "extra_env_var_keys"


def test__extra_env_var_keys(extra_env_var_keys):
    """Validate that fixture returns default for extra keys."""
    assert_that(extra_env_var_keys).is_equal_to([])


def test__extra_env_var_keys__couple_defined(pytester):
    """Fixture detects extra env var keys, if supplied."""
    patches = """
        @pytest.fixture(scope="session")
        def configuration_extra_env_var_keys():
            return ["ENV1", "ENV2"]
        """
    pytester.makeconftest(
        CONFTEST_TEMPLATE.format(fixture_name=FIXTURE_UNDER_TEST, patches=patches)
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
    perform_fixture_test_with_optional_log_capture(pytester)


def test__extra_env_var_keys__none(pytester, caplog):
    """Fixture should return the default and log a warning for invalid keys list."""

    patches = """
        @pytest.fixture(scope="session")
        def configuration_extra_env_var_keys():
            return None
        """
    pytester.makeconftest(
        CONFTEST_TEMPLATE.format(fixture_name=FIXTURE_UNDER_TEST, patches=patches)
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(extra_env_var_keys):
            assert_that(extra_env_var_keys).is_equal_to([])
    """
    )
    msg = {
        "target_level": logging.WARNING,
        "target_message_re": "Fixture configuration_extra_env_var_keys may only return "
        "a list of strings",
    }
    perform_fixture_test_with_optional_log_capture(
        pytester, caplog=caplog, target_messages=msg
    )


def test__extra_env_var_keys__empty_list(pytester, caplog):
    """Fixture should not error or log message if supplied an empty list."""
    patches = """
        @pytest.fixture(scope="session")
        def configuration_extra_env_var_keys():
            return []
        """
    pytester.makeconftest(
        CONFTEST_TEMPLATE.format(fixture_name=FIXTURE_UNDER_TEST, patches=patches)
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(extra_env_var_keys):
            assert_that(extra_env_var_keys).is_equal_to([])
    """
    )
    perform_fixture_test_with_optional_log_capture(pytester)
    target_message_re = (
        "Fixture configuration_extra_env_var_keys may only return a list of strings"
    )
    not_logged, matches = message_was_not_logged(
        caplog, target_message_re=target_message_re
    )
    assert_that(not_logged, f"Matching messages {matches}").is_true()


def test__extra_env_var_keys__invalid_type_in_list(pytester, caplog):
    """Fixture should return the default and log a warning for invalid keys list."""

    patches = """
        @pytest.fixture(scope="session")
        def configuration_extra_env_var_keys():
            return ["a string", {}]
        """
    pytester.makeconftest(
        CONFTEST_TEMPLATE.format(fixture_name=FIXTURE_UNDER_TEST, patches=patches)
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(extra_env_var_keys):
            assert_that(extra_env_var_keys).is_equal_to([])
    """
    )
    msg = {
        "target_level": logging.WARNING,
        "target_message_re": "Fixture configuration_extra_env_var_keys may only return "
        "a list of strings",
    }
    perform_fixture_test_with_optional_log_capture(
        pytester, caplog=caplog, target_messages=msg
    )


def test__extra_env_var_keys__not_a_list(pytester, caplog):
    """Fixture should return the default and log a warning for invalid keys list."""

    patches = """
        @pytest.fixture(scope="session")
        def configuration_extra_env_var_keys():
            return {"key":"value"}
        """
    pytester.makeconftest(
        CONFTEST_TEMPLATE.format(fixture_name=FIXTURE_UNDER_TEST, patches=patches)
    )

    # create a temporary pytest test file
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(extra_env_var_keys):
            assert_that(extra_env_var_keys).is_equal_to([])
    """
    )
    msg = {
        "target_level": logging.WARNING,
        "target_message_re": "Fixture configuration_extra_env_var_keys may only return "
        "a list of strings",
    }
    perform_fixture_test_with_optional_log_capture(
        pytester, caplog=caplog, target_messages=msg
    )
