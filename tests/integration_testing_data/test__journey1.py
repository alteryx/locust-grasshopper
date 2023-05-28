import logging

from locust import between, task

from grasshopper.lib.grasshopper import BaseJourney, Grasshopper
from grasshopper.lib.util.utils import custom_trend, check

logger = logging.getLogger(__name__)


class Journey1(BaseJourney):
    wait_time = between(min_wait=1, max_wait=2)
    defaults = {"thresholds": {
        "PX_TREND_google_home": {"type": "custom", "limit": 200},
        "google_home": {"type": "custom", "limit": 200}}}

    @task
    @custom_trend("PX_TREND_google_home")
    def journey1_task(self):
        logger.info(f"VU {self.vu_number}: Starting journey1_task")
        response = self.client.get("https://google.com", name="google_home")
        check("Status code is good",
              response.status_code < 400,
              self.environment)
        logger.info(f"VU {self.vu_number}: Google result: {response.status_code}")


def test_journey1(complete_configuration):
    complete_configuration["runtime"] = 20
    Journey1.update_incoming_scenario_args(complete_configuration)
    locust_env = Grasshopper.launch_test(Journey1, **complete_configuration)
    return locust_env
