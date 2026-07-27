"""Locust custom listeners.

The listeners module contains all the custom listeners that we have defined for Locust.
"""

import logging
from datetime import datetime, timezone

from grasshopper.lib.util.check_constants import CheckConstants
from grasshopper.lib.util.datadog_listener import DatadogApiListener
from grasshopper.lib.util.utils import (
    report_checks_to_console,
    report_thresholds_to_console,
)
from locust import events
from locust.env import Environment
from locust_influxdb_listener import InfluxDBListener, InfluxDBSettings

logger = logging.getLogger()


class GrasshopperListeners:
    """All of the hooks used to report custom metrics/checks to dbs/the console."""

    influxdb_listener: InfluxDBListener = None
    datadog_listener: DatadogApiListener = None
    locust_environment: Environment

    def __init__(self, environment: Environment):
        """Initialize for the given locust environment."""
        environment.events.test_start.add_listener(self.on_test_start)
        environment.events.test_stop.add_listener(self.on_test_stop_append_metric_data)
        self.locust_environment = environment

    @events.test_start.add_listener
    def on_test_start(self, environment: Environment, **_kwargs):
        """Create listeners for the configured metrics backends."""
        influx_configuration = environment.grasshopper.influx_configuration
        influx_host = influx_configuration.get("influx_host")

        if influx_host:
            logger.info(
                f"All collected metrics reported to influxdb host `{influx_host}`"
            )
            influx_db_settings = InfluxDBSettings(
                **influx_configuration,
                database="locust",
            )
            # start listener with the given configuration
            self.influxdb_listener = InfluxDBListener(
                env=environment, influxDbSettings=influx_db_settings
            )
        else:
            logger.info(
                "InfluxDB host was not specified. Skipping influxdb listener "
                "initialization..."
            )

        datadog_configuration = environment.grasshopper.datadog_configuration
        api_key = datadog_configuration.get("api_key")
        if api_key:
            logger.info(
                "All collected metrics reported to Datadog API site `%s`",
                datadog_configuration.get("site"),
            )
            self.datadog_listener = DatadogApiListener(
                environment=environment,
                **datadog_configuration,
            )
        else:
            logger.info(
                "DD_API_KEY and DD_ENV were not both specified. "
                "Skipping Datadog listener initialization..."
            )

    @events.test_stop.add_listener
    def on_test_stop_append_metric_data(self, environment, **_kwargs):
        """Create a listener which appends metrics to the environment.stats object."""
        try:
            self._append_trend_data(environment)
        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"Unexpected exception appending trend data to environment object: {e}"
            )
        try:
            self._append_checks_data(environment)
        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"Unexpected exception appending trend data to environment object: {e}"
            )
        self._send_to_datadog("shutdown", "close")

    def flush_check_to_dbs(self, check_name: str, check_passed: bool, extra_tags: dict):
        """Flush a check datapoint to whatever grasshopper dbs are being used."""
        environment_base_url = self.locust_environment.host
        tags = {"check_name": check_name, "environment": environment_base_url}
        if hasattr(self.locust_environment, "extra_context"):
            tags.update(self.locust_environment.extra_context)
        tags.update(extra_tags)
        fields = {"check_passed": int(check_passed)}
        time = datetime.now(timezone.utc)

        if self.influxdb_listener is not None:
            point = self.influxdb_listener._InfluxDBListener__make_data_point(
                "locust_checks", fields, time, tags=tags
            )
            self.influxdb_listener.cache.append(point)
        self._send_to_datadog(
            "check metric",
            "record_check",
            check_name=check_name,
            check_passed=check_passed,
            extra_tags=tags,
            time=time,
        )

    def write_metric_point(
        self, measurement: str, fields: dict, time=None, tags: dict | None = None
    ):
        """Write a custom point to every configured metrics backend."""
        metric_tags = tags or {}

        if self.influxdb_listener is not None:
            point = self.influxdb_listener._InfluxDBListener__make_data_point(
                measurement,
                fields,
                time or datetime.now(timezone.utc),
                tags=metric_tags,
            )
            self.influxdb_listener.cache.append(point)

        self._send_to_datadog(
            "custom metric",
            "write_point",
            measurement=measurement,
            fields=fields,
            time=time,
            tags=metric_tags,
        )

    def _send_to_datadog(self, operation: str, method_name: str, *args, **kwargs):
        datadog_listener = getattr(self, "datadog_listener", None)
        if datadog_listener is None:
            return
        try:
            getattr(datadog_listener, method_name)(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to send Datadog %s: %s", operation, exc)

    @staticmethod
    def _append_trend_data(environment):
        if (
            hasattr(environment.stats, "trends")
            and type(environment.stats.trends) is dict
        ):
            for trend_name, trend_values in environment.stats.trends.items():
                for threshold_object in trend_values.get("thresholds", []):
                    threshold_object["actual_value_in_ms"] = environment.stats.get(
                        trend_name, threshold_object["http_method"]
                    ).get_response_time_percentile(threshold_object["percentile"])
                    # the threshold passes if it has a non-zero value (zero means that
                    # the completion trigger never fired for this trend) - this
                    # typically is a functional defect or test problem
                    # AND the actual value is under the threshold set
                    threshold_object["succeeded"] = (
                        threshold_object["actual_value_in_ms"] > 0
                        and threshold_object["actual_value_in_ms"]
                        <= threshold_object["less_than_in_ms"]
                    )

            report_thresholds_to_console(environment.stats.trends)
        else:
            logger.info("No threshold data to report.")

    @staticmethod
    def _append_checks_data(environment):
        if (
            hasattr(environment.stats, "checks")
            and type(environment.stats.checks) is dict
        ):
            # mark all checks as passed or failed based on multiple criteria
            for check_item in environment.stats.checks.values():
                checks_passed = check_item.get("passed", 0)
                checks_total = check_item.get("total", 0)

                # add some calculated values, for convenience of consumers
                check_item["percentage_passed"] = (
                    (checks_passed / checks_total) if checks_total > 0 else 1
                )
                check_item["percentage_passed_display"] = round(
                    check_item["percentage_passed"] * 100, 2
                )

                # add a final "verdict" for this check
                if checks_total == checks_passed:
                    verdict = CheckConstants.VERDICT_ALL_PASSED
                elif check_item["percentage_passed"] >= check_item["warning_threshold"]:
                    verdict = CheckConstants.VERDICT_PASSED_RATE_OVER_THRESHOLD
                else:
                    verdict = CheckConstants.VERDICT_FAILED

                check_item["verdict"] = verdict

            report_checks_to_console(environment.stats.checks)
        else:
            logger.info("No checks data to report.")
