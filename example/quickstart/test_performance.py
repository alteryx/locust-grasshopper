"""A repeatable performance suite with explicit pass/fail criteria."""

from grasshopper.lib.configuration.gh_configuration import GHConfiguration
from grasshopper.lib.grasshopper import Grasshopper
from grasshopper.lib.journeys.base_journey import BaseJourney
from grasshopper.lib.util.utils import check
from locust import constant, task


class CatalogJourney(BaseJourney):
    """Repeatedly browse the product catalog."""

    wait_time = constant(0.1)
    defaults = {
        "thresholds": {"/products": {"type": "GET", "percentile": 0.95, "limit": 500}}
    }

    @task
    def browse(self) -> None:
        """Check that the product catalog contains items."""
        response = self.client.get("/products")
        check(
            "catalog is not empty",
            response.status_code == 200 and bool(response.json().get("items")),
            env=self.environment,
        )


def test_catalog_performance(
    complete_configuration: GHConfiguration, local_api: str
) -> None:
    """Require a non-empty catalog and a p95 response time at or below 500 ms."""
    CatalogJourney.host = local_api
    environment = Grasshopper.launch_test(CatalogJourney, **complete_configuration)

    # Locust records journey errors instead of raising them in the pytest test.
    assert not environment.runner.exceptions, environment.runner.exceptions
    stats = environment.stats.total
    assert stats.num_requests > 0, "The workload did not make any requests"
    assert stats.num_failures == 0, environment.stats.errors
    catalog_check = environment.stats.checks["catalog is not empty"]
    assert catalog_check["total"] > 0
    assert catalog_check["failed"] == 0, catalog_check
    threshold = environment.stats.trends["/products"]["thresholds"][0]
    assert threshold["succeeded"], threshold
