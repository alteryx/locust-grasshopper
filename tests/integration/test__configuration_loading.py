import logging

from assertpy import assert_that

from grasshopper.lib.configuration.gh_configuration import GHConfiguration

logger = logging.getLogger(__name__)


def test__complete_configuration__simplest_case(complete_configuration):
    """Validate the whole 'stack' of fixtures that produce complete_configuration.

    This test validates that all the fixtures feed into complete_configuration without
    errors and that the result of the entire process is a GHConfiguration object with
    about the right amount (currently there are 12, but this may change if more
    defaults are added).

    Note that in this case, most of the fixtures are not contributing additional
    values.

    """
    logger.debug(f"COMPLETE CONFIGURATION: {complete_configuration}")

    assert_that(complete_configuration).is_instance_of(GHConfiguration)
    # without supplying much, complete configuration should be >=12 items
    assert_that(len(complete_configuration)).is_greater_than(11)
