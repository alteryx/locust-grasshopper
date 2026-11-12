"""Locust custom listeners.

The listeners module contains all the custom listeners that we have defined for Locust.
"""

import logging
import warnings
from collections.abc import Mapping
from datetime import datetime, timezone

import gevent
from grasshopper.lib.util.check_constants import CheckConstants
from grasshopper.lib.util.datadog_listener import (
    DATADOG_TAG_KEYS,
    DatadogApiListener,
)
from grasshopper.lib.util.utils import (
    report_checks_to_console,
    report_thresholds_to_console,
)
from locust import events
from locust.env import Environment

# The archived influxdb client uses utcfromtimestamp(0) for its epoch constant.
# Limit this workaround to that warning during import; preserve caller filters.
with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore",
        message=r"datetime\.datetime\.utcfromtimestamp\(\) is deprecated",
        category=DeprecationWarning,
        module=r"influxdb\.line_protocol$",
    )
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
        self._user_metrics_greenlet = None

    @events.test_start.add_listener
    def on_test_start(self, environment: Environment, **_kwargs):
        """Create a listener for the test start event, starts an influxdb connection."""
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
            logger.debug(
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
            logger.debug(
                "DD_API_KEY and DD_ENV were not both specified. "
                "Skipping Datadog listener initialization..."
            )
        self._start_user_metrics(environment)

    @events.test_stop.add_listener
    def on_test_stop_append_metric_data(self, environment, **_kwargs):
        """Create a listener which appends metrics to the environment.stats object."""
        self._stop_user_metrics(environment)
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

    @staticmethod
    def _user_metric_tags(environment):
        """Return low-cardinality tags for environment-level load metrics."""
        configuration = getattr(environment.grasshopper, "global_configuration", {})
        if not isinstance(configuration, Mapping):
            return {"test_type": "exploratory", "scope": "environment"}
        test_type = configuration.get("test_type") or "exploratory"
        tags = {"test_type": str(test_type), "scope": "environment"}
        scenario_name = configuration.get("scenario_name")
        if scenario_name:
            tags["cuj"] = str(scenario_name)
        return tags

    @staticmethod
    def _configured_users(environment):
        shape = getattr(environment, "shape_class", None)
        users = getattr(shape, "users", None)
        if not isinstance(users, (int, float)):
            users = getattr(environment.grasshopper, "global_configuration", {}).get(
                "users"
            )
        return users if isinstance(users, (int, float)) else None

    def _start_user_metrics(self, environment):
        """Publish configured load and sample active users during the run."""
        configured_users = self._configured_users(environment)
        if configured_users is not None:
            self.write_metric_point(
                "locust_users",
                {"configured": int(configured_users)},
                tags=self._user_metric_tags(environment),
            )

        runner = getattr(environment, "runner", None)
        if runner is None or not isinstance(getattr(runner, "user_count", None), int):
            return
        self._user_metrics_greenlet = gevent.spawn(
            self._sample_active_users, environment
        )

    def _sample_active_users(self, environment):
        while True:
            runner = getattr(environment, "runner", None)
            active_users = getattr(runner, "user_count", 0)
            self.write_metric_point(
                "locust_users",
                {"active": int(active_users)},
                tags=self._user_metric_tags(environment),
            )
            gevent.sleep(1)

    def _stop_user_metrics(self, environment):
        """Stop active-user sampling and publish the terminal zero point."""
        if self._user_metrics_greenlet is not None:
            self._user_metrics_greenlet.kill(block=False)
            self._user_metrics_greenlet = None
        self.write_metric_point(
            "locust_users",
            {"active": 0},
            tags=self._user_metric_tags(environment),
        )

    @staticmethod
    def _configured_scenario_name(environment):
        """Resolve a scenario name from Grasshopper configuration."""
        configuration = getattr(environment.grasshopper, "global_configuration", {})
        if not isinstance(configuration, Mapping):
            return None
        scenario_name = configuration.get("scenario_name")
        return str(scenario_name) if scenario_name else None

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
        datadog_tags = {
            key: value for key, value in tags.items() if key in DATADOG_TAG_KEYS
        }
        datadog_tags.pop("cuj", None)
        datadog_tags.pop("scenario_name", None)
        scenario_name = self._configured_scenario_name(self.locust_environment)
        if scenario_name is not None:
            datadog_tags["scenario_name"] = scenario_name
        self._send_to_datadog(
            "check metric",
            "record_check",
            check_name=check_name,
            check_passed=check_passed,
            extra_tags=datadog_tags,
            time=time,
        )

    def write_metric_point(
        self, measurement: str, fields: dict, time=None, tags: dict | None = None
    ):
        """Fan out one custom metric point to InfluxDB and Datadog when enabled."""
        metric_tags = tags or {}

        if self.influxdb_listener is not None:
            point = self.influxdb_listener._InfluxDBListener__make_data_point(
                measurement,
                fields,
                time or datetime.now(timezone.utc),
                tags=metric_tags,
            )
            self.influxdb_listener.cache.append(point)

        datadog_tags = {
            key: value for key, value in metric_tags.items() if key in DATADOG_TAG_KEYS
        }
        datadog_tags.pop("cuj", None)
        datadog_tags.pop("scenario_name", None)
        scenario_name = self._configured_scenario_name(self.locust_environment)
        if scenario_name is not None:
            datadog_tags["scenario_name"] = scenario_name
        self._send_to_datadog(
            "custom metric",
            "record_custom_point",
            measurement=measurement,
            fields=fields,
            time=time,
            tags=datadog_tags,
        )

    def _send_to_datadog(self, operation: str, method_name: str, *args, **kwargs):
        """Call a Datadog listener method when Datadog reporting is configured."""
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
            for check_key, check_item in environment.stats.checks.items():
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
            logger.info("No named Grasshopper checks were recorded.")
