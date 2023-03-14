# import gevent
# import locust
import pytest

# from locust.env import Environment
# from locust.stats import stats_printer
#
# from grasshopper.lib.journeys.PhotonFlow_LocustFile import PhotonFlowJourney
# from grasshopper.lib.util.listeners import initialize_listeners
# from grasshopper.lib.util.shapes import TrendShape


@pytest.mark.trend
@pytest.mark.parametrize(
    ("wrangled_dataset_id", "thresholds", "tags"),
    [
        (
            1160930,
            {
                "{CUSTOM}PX_TREND_photon_flow_run": 55000,
                "{GET}poll_job_group_status": 3000,
            },
            {"run_type": "trend"},
        ),
        (
            1121086,
            {
                "{CUSTOM}PX_TREND_photon_flow_run": 65000,
                "{GET}poll_job_group_status": 2000,
            },
            {"run_type": "trend"},
        ),
    ],
)
def test__run_flow(custom_args, wrangled_dataset_id, thresholds, tags):
    pass
    # # pass in parameters to the test itself
    # PhotonFlowJourney.test_parameters = {
    #     "wrangled_dataset_id": wrangled_dataset_id,
    #     "thresholds": thresholds,
    #     "tags": tags,
    # }
    # PhotonFlowJourney.command_line_arguments = custom_args
    #
    # # kick off a test, probably this would be re-usable method used by all tests
    # # TODO: CLEANUP, make this chunk of code into a re-usable method in a separate
    #  file
    # # make a lib dir for this and shapes etc. ??
    # env = Environment(user_classes=[PhotonFlowJourney])
    # env.create_local_runner()
    # env.runner.stats.reset_all()
    # gevent.spawn(stats_printer(env.stats))
    # gevent.spawn(locust.stats.stats_history, env.runner)
    # initialize_listeners(env)
    # env.runner.start(
    #     1, spawn_rate=1, wait=True
    # )  # these would also be loaded from custom_args, just like journeys time
    # gevent.spawn_later(custom_args["RUN_TIME_PER_TEST"], lambda: env.runner.quit())
    # env.runner.greenlet.join()
    #
    # print(env.runner.stats.__dict__)  # just to show what is in there, roughly


@pytest.mark.trend
@pytest.mark.debug
def test__import_flow(custom_args):
    # # pass in parameters to the test itself
    # PhotonFlowJourney.test_parameters = {"wrangled_dataset_id": 1160930}
    # PhotonFlowJourney.command_line_arguments = custom_args
    #
    # # kick off a test, probably this would be re-usable method used by all tests
    # env = Environment(user_classes=[PhotonFlowJourney])
    # env.create_local_runner()
    # env.runner.stats.reset_all()
    # gevent.spawn(stats_printer(env.stats))
    # gevent.spawn(locust.stats.stats_history, env.runner)
    # env.shape_class = TrendShape()
    # env.runner.start_shape()
    # gevent.spawn_later(custom_args["RUN_TIME_PER_TEST"], lambda: env.runner.quit())
    # env.runner.greenlet.join()
    #
    # print(env.runner.stats.__dict__)  # just to show what is in there, roughly
    pass
