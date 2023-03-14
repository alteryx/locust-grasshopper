"""Fake Locust File.

This can be run individually or as part of a larger journey in pytest. Obviously,
doesn't really do anything interesting, but does make an http call to a public api.
This file is used to test the integration of pytest/locust/grasshopper.
"""
from locust import between, run_single_user

from grasshopper.lib.journeys.base_journey import BaseJourney
from grasshopper.lib.util.metrics import task


class FakeJourney(BaseJourney):
    """Fake Journey for testing Journey construction."""

    wait_time = between(1, 2)

    @task(4)
    def fake_test_weather(self):
        """Fake task, simply hits a public api."""
        print(
            f"This method's locust_task_weight attr == "
            f"{self.fake_test_weather.locust_task_weight}"
        )
        result = self.client.get("https://api.weather.gov/")
        print(f"{self.client_id} RESULT {result.status_code} : {result.text}")


if __name__ == "__main__":
    run_single_user(FakeJourney)
