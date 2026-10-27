"""A repeatable performance suite with explicit pass/fail criteria."""

from grasshopper.lib.configuration.gh_configuration import GHConfiguration
from grasshopper.lib.grasshopper import Grasshopper
from grasshopper.lib.journeys.base_journey import BaseJourney
from locust import constant, task


class CatalogJourney(BaseJourney):
    """Repeatedly browse the product catalog."""

    wait_time = constant(0.1)
    defaults = {
        "thresholds": {"/products": {"type": "GET", "percentile": 0.95, "limit": 500}}
    }

    @task
    def browse(self) -> None:
        """Count an empty catalog response as a failed request."""
        with self.client.get("/products", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Expected HTTP 200, got {response.status_code}")
            elif not response.json().get("items"):
                response.failure("Expected non-empty items")


def test_catalog_performance(
    complete_configuration: GHConfiguration, local_api: str
) -> None:
    """Require successful requests and a p95 response time at or below 500 ms."""
    CatalogJourney.host = local_api
    environment = Grasshopper.launch_test(CatalogJourney, **complete_configuration)

    # Locust records journey errors instead of raising them in the pytest test.
    assert not environment.runner.exceptions, environment.runner.exceptions
    stats = environment.stats.get("/products", "GET")
    assert stats.num_requests > 0, "The workload did not make any requests"
    assert stats.num_failures == 0, environment.stats.errors
    threshold = environment.stats.trends["/products"]["thresholds"][0]
    assert threshold["succeeded"], threshold
