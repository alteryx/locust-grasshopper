from assertpy import assert_that

# Alteryx Packages
from grasshopper.lib.fixtures.grasshopper_constants import GrasshopperConstants
from grasshopper.lib.util.shapes import Default


def test_grasshopper_attr_names(grasshopper_attr_names):
    expected_attr_names = GrasshopperConstants.GRASSHOPPER_ATTR_NAMES
    assert grasshopper_attr_names == expected_attr_names


# expecting all 10 values because these are being set in the commandline in the
# `set_base_scenario_file_args_all` fixture.
def test_scenario_content_no_scenario(scenario_content):
    expected_scenario_content = None
    assert scenario_content == expected_scenario_content


def test_grasshopper_scenario_args_no_scenario(grasshopper_scenario_args):
    expected_scenario_args = {}
    assert grasshopper_scenario_args == expected_scenario_args


def test_grasshopper_scenario_file_set_args_no_scenario(
    grasshopper_scenario_file_set_args,
):
    expected_scenario_args = {
        "cleanup_s3": True,
        "runtime": GrasshopperConstants.RUNTIME_DEFAULT,
        "scenario_delay": GrasshopperConstants.SCENARIO_DELAY_DEFAULT,
        "shape": GrasshopperConstants.SHAPE_DEFAULT,
        "spawn_rate": GrasshopperConstants.SPAWN_RATE_DEFAULT,
        "users": GrasshopperConstants.USERS_DEFAULT,
    }
    assert expected_scenario_args.items() <= grasshopper_scenario_file_set_args.items()
    assert_that(grasshopper_scenario_file_set_args["shape_instance"]).is_instance_of(
        Default
    )


def test_grasshopper_base_args(grasshopper_base_args):
    expected_base_args = {
        "cleanup_s3": True,
        "runtime": GrasshopperConstants.RUNTIME_DEFAULT,
        "scenario_delay": GrasshopperConstants.SCENARIO_DELAY_DEFAULT,
        "shape": GrasshopperConstants.SHAPE_DEFAULT,
        "spawn_rate": GrasshopperConstants.SPAWN_RATE_DEFAULT,
        "users": GrasshopperConstants.USERS_DEFAULT,
    }
    assert expected_base_args.items() <= grasshopper_base_args.items()
    assert_that(grasshopper_base_args["shape_instance"]).is_instance_of(Default)


def test_grasshopper_base_args_with_shape_processed(
    grasshopper_args_with_shape_processed,
):
    expected_shape_processed_args = {
        "cleanup_s3": True,
        "runtime": GrasshopperConstants.RUNTIME_DEFAULT,
        "scenario_delay": GrasshopperConstants.SCENARIO_DELAY_DEFAULT,
        "shape": GrasshopperConstants.SHAPE_DEFAULT,
        "spawn_rate": GrasshopperConstants.SPAWN_RATE_DEFAULT,
        "users": GrasshopperConstants.USERS_DEFAULT,
    }
    assert (
        expected_shape_processed_args.items()
        <= grasshopper_args_with_shape_processed.items()
    )
    assert_that(grasshopper_args_with_shape_processed["shape_instance"]).is_instance_of(
        Default
    )


def test_grasshopper_args_type_cast(grasshopper_args_type_cast):
    assert type(grasshopper_args_type_cast["runtime"]) == float
    assert type(grasshopper_args_type_cast["users"]) == int
    assert type(grasshopper_args_type_cast["spawn_rate"]) == float
    assert type(grasshopper_args_type_cast["scenario_delay"]) == float


def test_grasshopper_args_none_set(grasshopper_args):
    expected_grasshopper_args = {
        "cleanup_s3": True,
        "runtime": GrasshopperConstants.RUNTIME_DEFAULT,
        "scenario_delay": GrasshopperConstants.SCENARIO_DELAY_DEFAULT,
        "shape": GrasshopperConstants.SHAPE_DEFAULT,
        "spawn_rate": GrasshopperConstants.SPAWN_RATE_DEFAULT,
        "users": GrasshopperConstants.USERS_DEFAULT,
    }
    assert expected_grasshopper_args.items() <= grasshopper_args.items()
    assert_that(grasshopper_args["shape_instance"]).is_instance_of(Default)
