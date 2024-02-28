import logging

from grasshopper.lib.grasshopper import Grasshopper
from grasshopper.lib.journeys.base_journey import BaseJourney
from grasshopper.lib.util.utils import check
from locust import between, task

logger = logging.getLogger(__name__)


class ExampleJourney(BaseJourney):
    """An example journey class with a simple task"""

    # number of seconds to wait between each task
    wait_time = between(min_wait=1, max_wait=4)

    # `host` is automatically prepended to all request endpoint
    # urls when using `self.client` requests. It is also set as the
    # global "environment" tag in timeseries metrics
    host = "https://google.com"

    # lower precedence scenario_args dict, merged in on startup
    defaults = {
        "foo": "bar",
    }

    # a locust task, repeated over and over again until the test finishes
    @task
    def example_task(self):
        """a simple get google images HTTP request"""
        logger.info(
            f"Beginning example task for VU {self.vu_number} with param `foo`="
            f'`{self.scenario_args.get("foo")}`'
        )
        # aggregate all metrics for this request under the name "get google images"
        # if name is not specified, then the full url will be the name of the metric
        response = self.client.get(
            "/imghp", name="get google images", context={"extra": "tag"}
        )
        logger.info(f"google images responded with a {response.status_code}.")
        check(
            "google images responded with a 200",
            response.status_code == 200,
            env=self.environment,
        )


def test_run_example_journey(complete_configuration, example_configuration_values):
    ExampleJourney.update_incoming_scenario_args(example_configuration_values)
    ExampleJourney.update_incoming_scenario_args(complete_configuration)
    locust_env = Grasshopper.launch_test(
        ExampleJourney,
        **complete_configuration,
    )
    return locust_env
