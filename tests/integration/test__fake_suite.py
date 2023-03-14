import logging

from FakeLocustFile import FakeJourney

from grasshopper.lib.grasshopper import Grasshopper

logger = logging.getLogger()


def test__test1(custom_args, add_workspace_token, grasshopper_args):
    FakeJourney.command_line_arguments = custom_args
    grasshopper_args["runtime"] = 5
    grasshopper_args["num_iterations"] = 2
    env = Grasshopper.launch_test([FakeJourney], **grasshopper_args)

    logger.info(f"Number of iterations [{env.stats.num_iterations}]")
    assert env.stats.num_iterations > 0, "num_iterations was not incremented"
