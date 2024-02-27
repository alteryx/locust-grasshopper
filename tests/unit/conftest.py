"""Module: Conftest."""
import logging
import re
from pathlib import Path

import pytest

pytest_plugins = ["pytester"]

CONFTEST_TEMPLATE = """
        import pytest
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration

        # import the fixture(s) we need to patch
        {patches}

        # import the fixture we want to test
        from grasshopper.lib.fixtures import {fixture_name}
    """

PYFILE_TEMPLATE = """
        from grasshopper.lib.configuration.gh_configuration import GHConfiguration
        from assertpy import assert_that

        def test_grasshopper_fixture({fixture_name}):
            assert_that({fixture_name}).is_instance_of(GHConfiguration)
            {validations}
    """

PYFILE_ASSERT_EMPTY_CONFIG = (
    "assert_that({fixture_name}).is_equal_to(GHConfiguration())"
)

PYFILE_ASSERT_EXPECTED_CONFIG = (
    "assert_that({fixture_name}).is_equal_to(GHConfiguration({expected}))"
)


@pytest.fixture(scope="session")
def current_global_defaults():
    # Note the reason that we have a _separate_ dict here with the current defaults,
    # is to be a cross check. If you were to grab the constant and do a calculation
    # similar to fixture we are checking, both can be empty and the test would pass
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


class MockConfig(dict):
    """Mock config object that can be loaded with a dict instead of a Config."""

    def getoption(self, value):
        """Retrieve a value from the dictionary, the way a Config object supports."""
        return self.get(value)


def was_message_logged(
    caplog,
    target_message_re=None,
    target_level=None,
    target_index=None,
    target_logger=None,
):
    """Validate that the specified message was logged.

    Validation is using only the criteria provided and skipping a check on any
    attribute that is None.

    Generally, parameter handling is meant to optimize the most common usage.

    pass target_index=-1 to get the very last message logged
    if you pass in a string for target_message_re, then will compile to re for you

    """
    # if the user didn't specify any targets, return true if any records exist in caplog
    if (
        target_message_re is None
        and target_level is None
        and target_index is None
        and target_level is None
    ):
        return len(caplog.record_tuples) > 0

    # otherwise, see if any records match
    if target_index:
        # get the target_index record, make it into a list for the search part
        record_tuples = [caplog.record_tuples[target_index]]
    else:
        # include all the records in caplog
        record_tuples = caplog.record_tuples

    # convert strings to a compiled regex
    target_message_re = make_re(target_message_re)

    matches = []  # collect the matching records
    for record_tuple in record_tuples:
        tuple_match = True
        log, level, msg = record_tuple

        # determine if this record matches
        if target_logger:
            tuple_match = tuple_match and log == target_logger
        if target_level:
            tuple_match = tuple_match and level == target_level
        if target_message_re:
            tuple_match = tuple_match and target_message_re.search(msg) is not None
        if tuple_match:
            matches.append(record_tuple)

    return len(matches) > 0, matches


def message_was_not_logged(
    caplog,
    target_message_re=None,
    target_level=None,
    target_index=None,
    target_logger=None,
):
    """Validate a message was _not_ logged using same matching as was_message_logged."""
    found, matches = was_message_logged(
        caplog,
        target_message_re=target_message_re,
        target_level=target_level,
        target_index=target_index,
        target_logger=target_logger,
    )
    return not found, matches


def make_re(potential_re):
    """Convert a string to a compiled re, otherwise return the value unaltered."""
    if type(potential_re) == str:
        potential_re = re.compile(potential_re, re.IGNORECASE)
    return potential_re


def calculate_path(filename, subdir="../fixture_testing_data"):
    """Calculate the absolute path to a file in the fixture_test_data directory."""
    path = Path(__file__).parent / Path(subdir) / filename

    return path


def perform_fixture_test_with_optional_log_capture(
    pytester,
    outcomes={"passed": 1},
    caplog=None,
    target_messages=[],
):
    """Perform the actual 'test' portion of a fixture test and validate the results.

    Generally, parameter handling is meant to optimize the most common usage.

    outcomes - the exact same values as you pass to pytester.assert_outcomes, see the
    pytester documentation for more details.

    caplog - Simply pass the value of the pytest supplied fixture called `caplog`,
    which your test will need to put into its signature.bWill only do a log capture if
    caplog is not None.

    target_messages - list of messages you expect to see in the captured logging for
    the test within a test. Only the non-None attributes are checked. Ignored if caplog
    is None. If you pass a single dict message for target_messages, we will make it
    into a list for you.

    """
    # Step 1: Run the test within the test
    if caplog:
        with caplog.at_level(logging.DEBUG):
            # run all tests with pytest
            result = pytester.runpytest()
    else:
        result = pytester.runpytest()

    # Step 2: Validate the outcomes from the test within the test
    result.assert_outcomes(**outcomes)

    # Step 3: Validate any log messages supplied
    if caplog:
        target_messages = convert_dict_to_list(target_messages)
        for target_message in target_messages:
            found, _ = was_message_logged(
                caplog,
                **target_message,
            )
            assert found

    # return the result from pytester.runpytest() so that a test
    # may perform additional validations not provided for here
    return result


def convert_dict_to_list(target_messages):
    """Convert a single dictionary to a list of that single dictionary.

    This is used to make the most common case (you only need to validate one message,
    therefore only one message dict) less wordy and easier.

    """
    if type(target_messages) == dict:
        target_messages = [target_messages]

    return target_messages
