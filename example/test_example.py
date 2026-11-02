"""A small performance test against httpbin's public HTTP demo API."""

from grasshopper.lib.configuration.gh_configuration import GHConfiguration
from grasshopper.lib.grasshopper import Grasshopper
from grasshopper.lib.journeys.base_journey import BaseJourney
from grasshopper.lib.util.utils import check
from locust import constant, task


class ExampleJourney(BaseJourney):
    """Request a URL and check that the API echoes it back."""

    host = "https://httpbin.org"
    wait_time = constant(1)
    defaults = {
        "thresholds": {"/get": {"type": "GET", "percentile": 0.95, "limit": 2000}}
    }

    @task
    def get_example(self) -> None:
        response = self.client.get("/get")
        check(
            "request URL is echoed",
            response.status_code == 200 and response.json().get("url") == response.url,
            env=self.environment,
        )


def test_run_example_journey(complete_configuration: GHConfiguration) -> None:
    environment = Grasshopper.launch_test(ExampleJourney, **complete_configuration)

    # Locust records journey errors instead of raising them in the pytest test.
    assert not environment.runner.exceptions, environment.runner.exceptions
    stats = environment.stats.total
    assert stats.num_requests > 0, "The workload did not make any requests"
    assert stats.num_failures == 0, environment.stats.errors
    echo_check = environment.stats.checks["request URL is echoed"]
    assert echo_check["total"] > 0
    assert echo_check["failed"] == 0, echo_check
    threshold = environment.stats.trends["/get"]["thresholds"][0]
    assert threshold["succeeded"], threshold
