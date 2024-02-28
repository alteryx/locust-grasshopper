from grasshopper.lib.configuration.gh_configuration import GHConfiguration

from tests.unit.conftest import (
    CONFTEST_TEMPLATE,
    PYFILE_ASSERT_EMPTY_CONFIG,
    PYFILE_ASSERT_EXPECTED_CONFIG,
    PYFILE_TEMPLATE,
    perform_fixture_test_with_optional_log_capture,
)

FIXTURE_UNDER_TEST = "pre_processed_args"


def test__pre_processed_args__happy(pytester):
    """Fixture should pass on the entries found for special keys, scenario_file and
    scenario_name."""

    expected_config_args = GHConfiguration(
        {
            "scenario_file": "fake_scenario_file.yaml",
            "scenario_name": "fake_scenario_name",
        }
    )

    patches = f"""
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
            config = GHConfiguration({expected_config_args})
            return config
        """
    pytester.makeconftest(
        CONFTEST_TEMPLATE.format(fixture_name=FIXTURE_UNDER_TEST, patches=patches)
    )

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


def test__pre_processed_args__empty_sources(pytester):
    """Fixture should return an empty config if all sources are empty."""

    patches = """
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
            config = GHConfiguration()
            return config
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


def test__pre_processed_args__with_precedence_applied(pytester):
    """Test fixture loads with the correct precedence applied.

    This test also covers some other test cases:
    + should be able to handle a source that is empty, in this case global defaults
    + should be able to handle a source that has extra, unrelated keys in addition to
    the keys it is looking for (config file args)
    + should be able to handle one key coming from one source and the other key coming
    from another source

    """

    patches = """
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
                "scenario_name": "from_env_var_this_is_the_one"})
            return config

        @pytest.fixture(scope="session")
        def cmdln_args():
            config = GHConfiguration({"scenario_file":
                "from_cmdln_this_is_the_one.yaml"})
            return config
        """
    pytester.makeconftest(
        CONFTEST_TEMPLATE.format(fixture_name=FIXTURE_UNDER_TEST, patches=patches)
    )

    expected_config_args = {
        "scenario_file": "from_cmdln_this_is_the_one.yaml",
        "scenario_name": "from_env_var_this_is_the_one",
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
