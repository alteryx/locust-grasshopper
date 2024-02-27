from unittest.mock import patch

from assertpy import assert_that
from grasshopper.lib.configuration.gh_configuration import (  # noqa: N817
    ConfigurationConstants as CC,
)
from grasshopper.lib.configuration.gh_configuration import GHConfiguration

# Alteryx Packages
# alias to make patches easier to read
from tests.unit.conftest import (  # noqa: I202
    CONFTEST_TEMPLATE,
    PYFILE_ASSERT_EMPTY_CONFIG,
    PYFILE_ASSERT_EXPECTED_CONFIG,
    PYFILE_TEMPLATE,
    perform_fixture_test_with_optional_log_capture,
)

FIXTURE_UNDER_TEST = "global_defaults"

ATTRS_WITH_NO_DEFAULTS = {
    "attr1": {
        "opts": ["--attr1"],
        "attrs": {
            "action": "store",
            "help": "Attr1",
        },
    },
    "attr2": {
        "opts": ["--attr2"],
        "attrs": {
            "action": "store",
            "help": "Attr2",
        },
    },
}

ATTRS_FEW_VALUES_AND_NOT_ALL_DEFAULTS = {
    "attr1": {
        "opts": ["--attr1"],
        "attrs": {
            "action": "store",
            "help": "Attr1",
        },
        "default": "Default 1",
    },
    "attr2": {
        "opts": ["--attr2"],
        "attrs": {
            "action": "store",
            "help": "Attr2",
        },
        "default": 2,
    },
    "attr3": {
        "opts": ["--attr3"],
        "attrs": {
            "action": "store",
            "help": "Attr3",
        },
    },
}


def test__global_defaults(current_global_defaults, global_defaults):
    """Test fixture matches the currently defined defaults in ATTRS."""
    assert_that(global_defaults).is_instance_of(GHConfiguration)
    assert_that(global_defaults).is_equal_to(current_global_defaults)


@patch.dict(CC.COMPLETE_ATTRS, ATTRS_FEW_VALUES_AND_NOT_ALL_DEFAULTS, clear=True)
def test__global_defaults__finds_defaults_in_arbitrary_attrs(pytester):
    """Fixture loads from an arbitrary COMPLETE_ATTRS."""

    pytester.makeconftest(
        CONFTEST_TEMPLATE.format(fixture_name=FIXTURE_UNDER_TEST, patches="")
    )
    expected_config_args = {
        "attr1": "Default 1",
        "attr2": 2,
    }
    pytester.makepyfile(
        PYFILE_TEMPLATE.format(
            fixture_name=FIXTURE_UNDER_TEST,
            validations=PYFILE_ASSERT_EXPECTED_CONFIG.format(
                fixture_name=FIXTURE_UNDER_TEST,
                expected=expected_config_args,
            ),
        ),
    )

    perform_fixture_test_with_optional_log_capture(pytester)


@patch.dict(CC.COMPLETE_ATTRS, ATTRS_WITH_NO_DEFAULTS, clear=True)
def test__global_defaults__no_defaults_in_attrs(pytester):
    """Test fixture doesn't raise an error if COMPLETE_ATTRS does not have any attrs
    with defaults defined."""

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


@patch.dict(CC.COMPLETE_ATTRS, clear=True)
def test__global_defaults__empty_attrs(pytester):
    """Fixture should not raise errors if configuration file is empty."""

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
