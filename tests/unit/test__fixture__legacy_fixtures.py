from assertpy import assert_that

# Alteryx Packages
from grasshopper.lib.configuration.gh_configuration import GHConfiguration


def test__grasshopper_scenario_args(grasshopper_scenario_args):
    # this fixture should always return {} now, but not removed in order to support
    # backwards compatibility
    assert_that(grasshopper_scenario_args).is_instance_of(GHConfiguration)
    assert_that(grasshopper_scenario_args).is_equal_to(GHConfiguration())


def test__grasshopper_args(complete_configuration, grasshopper_args):
    # grasshopper_args fixture should just match the complete_configuration fixture
    # now, similarly kept around for backwards compatibility
    assert_that(grasshopper_args).is_instance_of(GHConfiguration)
    assert_that(grasshopper_args).is_equal_to(complete_configuration)
