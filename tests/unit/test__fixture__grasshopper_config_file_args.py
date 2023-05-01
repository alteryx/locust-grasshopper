import logging

from tests.unit.conftest import (
    CONFTEST_TEMPLATE,
    PYFILE_ASSERT_EMPTY_CONFIG,
    PYFILE_ASSERT_EXPECTED_CONFIG,
    PYFILE_TEMPLATE,
    calculate_path,
    perform_fixture_test_with_optional_log_capture,
)

FIXTURE_UNDER_TEST = "grasshopper_config_file_args"


def test__grasshopper_config_file_args__happy(pytester):
    # calculate the path before going into the other pytest context
    mock_config_file_path = calculate_path("mock_basic.config")

    patches = f"""@pytest.fixture(scope="session")
        def grasshopper_config_file_path():
            return '{mock_config_file_path}'
        """
    pytester.makeconftest(
        CONFTEST_TEMPLATE.format(fixture_name=FIXTURE_UNDER_TEST, patches=patches)
    )
    expected_config_args = {
        "influx": True,
        "users": 1.0,
        "spawn_rate": 1.0,
        "runtime": 600,
        "flow_name": "POC flow",
        "recipe_name": "Untitled recipe",
        "engine": "photon",
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


def test__grasshopper_config_file_args__file_not_found(pytester, caplog):
    """Fixture should log a warning and return an empty config if path not found."""
    mock_config_file_path = calculate_path("bogus.config")

    patches = f"""@pytest.fixture(scope="session")
        def grasshopper_config_file_path():
            return '{mock_config_file_path}'
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
    msg = {
        "target_level": logging.WARNING,
        "target_message_re": "Skipping loading from grasshopper configuration file "
        "because (.+) not found",
    }
    perform_fixture_test_with_optional_log_capture(
        pytester, caplog=caplog, target_messages=msg
    )


def test__grasshopper_config_file_args__missing_section(pytester):
    """Fixture should silently ignore a missing section."""
    mock_config_file_path = calculate_path("mock_missing_section.config")

    patches = f"""@pytest.fixture(scope="session")
        def grasshopper_config_file_path():
            return '{mock_config_file_path}'
        """
    pytester.makeconftest(
        CONFTEST_TEMPLATE.format(fixture_name=FIXTURE_UNDER_TEST, patches=patches)
    )
    expected_config_args = {
        "influx": True,
        "flow_name": "POC flow",
        "recipe_name": "Untitled recipe",
        "engine": "photon",
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


def test__grasshopper_config_file_args__extra_section(pytester):
    """Fixture should silently ignore any extra section(s)."""
    mock_config_file_path = calculate_path("mock_extra_section.config")

    patches = f"""@pytest.fixture(scope="session")
        def grasshopper_config_file_path():
            return '{mock_config_file_path}'
        """
    pytester.makeconftest(
        CONFTEST_TEMPLATE.format(fixture_name=FIXTURE_UNDER_TEST, patches=patches)
    )
    expected_config_args = {
        "influx": True,
        "flow_name": "POC flow",
        "recipe_name": "Untitled recipe",
        "engine": "photon",
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


def test__grasshopper_config_file_args__invalid_yaml(pytester, caplog):
    """Fixture should log a warning and return an empty config if not valid yaml."""
    mock_config_file_path = calculate_path("mock_invalid_yaml.config")

    patches = f"""@pytest.fixture(scope="session")
        def grasshopper_config_file_path():
            return '{mock_config_file_path}'
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
    msg = {
        "target_level": logging.WARNING,
        "target_message_re": "Unable to parse yaml file",
    }
    perform_fixture_test_with_optional_log_capture(
        pytester, caplog=caplog, target_messages=msg
    )


def test__grasshopper_config_file_args__empty_yaml(pytester, caplog):
    """Fixture should log a warning and return an empty config if file is empty."""
    mock_config_file_path = calculate_path("mock_empty_yaml.config")

    patches = f"""@pytest.fixture(scope="session")
        def grasshopper_config_file_path():
            return '{mock_config_file_path}'
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
    msg = {
        "target_level": logging.WARNING,
        "target_message_re": "Unable to parse yaml file",
    }
    perform_fixture_test_with_optional_log_capture(
        pytester, caplog=caplog, target_messages=msg
    )
