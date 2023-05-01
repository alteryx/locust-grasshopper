import logging

from assertpy import assert_that

from tests.unit.conftest import (  # noqa: I202
    CONFTEST_TEMPLATE,
    perform_fixture_test_with_optional_log_capture,
)

FIXTURE_UNDER_TEST = "env_var_prefix_key"


def test__env_var_prefix_key_default(env_var_prefix_key):
    """Validate default value is supplied for prefix."""
    assert_that(env_var_prefix_key).is_equal_to("GH_")


def test__env_var_prefix_key__with_diff_prefix(pytester):
    """Fixture should return an alternate prefix when supplied."""
    patches = """
        @pytest.fixture(scope="session")
        def configuration_prefix_key():
            return 'MY_'
        """
    pytester.makeconftest(
        CONFTEST_TEMPLATE.format(fixture_name=FIXTURE_UNDER_TEST, patches=patches)
    )
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(env_var_prefix_key):
            assert_that(env_var_prefix_key).is_equal_to('MY_')
    """
    )

    perform_fixture_test_with_optional_log_capture(pytester)


def test__env_var_prefix_key__with_empty_prefix_str(pytester, caplog):
    """Fixture should fall bqck to the default if invalid prefix is supplied."""

    patches = """
        @pytest.fixture(scope="session")
        def configuration_prefix_key():
            return ''
        """
    pytester.makeconftest(
        CONFTEST_TEMPLATE.format(fixture_name=FIXTURE_UNDER_TEST, patches=patches)
    )
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(env_var_prefix_key):
            assert_that(env_var_prefix_key).is_equal_to('GH_')
    """
    )
    msg = {
        "target_level": logging.WARNING,
        "target_message_re": "Fixture configuration_prefix_key may only be a non zero "
        "length str",
    }
    perform_fixture_test_with_optional_log_capture(
        pytester, caplog=caplog, target_messages=msg
    )


def test__env_var_prefix_key__prefix_is_none(pytester, caplog):
    """Fixture should fall bqck to the default if invalid prefix is supplied."""

    patches = """
        @pytest.fixture(scope="session")
        def configuration_prefix_key():
            return None
        """
    pytester.makeconftest(
        CONFTEST_TEMPLATE.format(fixture_name=FIXTURE_UNDER_TEST, patches=patches)
    )
    pytester.makepyfile(
        """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture(env_var_prefix_key):
            assert_that(env_var_prefix_key).is_equal_to('GH_')
    """
    )
    msg = {
        "target_level": logging.WARNING,
        "target_message_re": "Fixture configuration_prefix_key may only be a non zero "
        "length str",
    }
    perform_fixture_test_with_optional_log_capture(
        pytester, caplog=caplog, target_messages=msg
    )
