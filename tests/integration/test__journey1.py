import logging

from grasshopper.lib.grasshopper import BaseJourney, Grasshopper
from grasshopper.lib.util.utils import custom_trend
from locust import between, task

logger = logging.getLogger(__name__)


class Journey1(BaseJourney):
    wait_time = between(min_wait=30, max_wait=40)
    defaults = {}

    @task
    @custom_trend("PX_TREND_google_home")
    def journey1_task(self):
        logger.info(f"VU {self.vu_number}: Starting journey1_task")
        response = self.client.get("https://google.com", name="google_home")
        logger.info(f"VU {self.vu_number}: Google result: {response.status_code}")


def test_journey1(complete_configuration):
    Journey1.update_incoming_scenario_args(complete_configuration)
    locust_env = Grasshopper.launch_test(Journey1, **complete_configuration)
    return locust_env
