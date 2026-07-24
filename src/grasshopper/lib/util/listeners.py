"""Locust custom listeners.

The listeners module contains all the custom listeners that we have defined for Locust.
"""

import json
import logging
import re
from datetime import datetime, timezone
from urllib import error, request

import gevent
from grasshopper.lib.util.check_constants import CheckConstants
from grasshopper.lib.util.utils import (
    report_checks_to_console,
    report_thresholds_to_console,
)
from locust import events
from locust.env import Environment
from locust_influxdb_listener import InfluxDBListener, InfluxDBSettings

logger = logging.getLogger()


class DatadogApiListener:
    """Forward Locust and custom metrics to the Datadog metrics API."""

    def __init__(
        self,
        environment: Environment,
        api_key: str,
        site: str = "datadoghq.com",
        namespace: str = "grasshopper",
        default_tags: dict | None = None,
        batch_size: int = 200,
        close_timeout: float = 5,
    ):
        self.environment = environment
        self.api_key = api_key
        self.site = site
        self.namespace = namespace.strip(".")
        self.default_tags = default_tags or {}
        self.batch_size = batch_size
        self.close_timeout = close_timeout
        self.series_buffer = []
        self._flush_greenlet = None
        environment.events.request.add_listener(self.on_request)

    def close(self):
        """Best-effort flush without allowing telemetry to block test shutdown."""
        try:
            self.environment.events.request.remove_listener(self.on_request)
        except (AttributeError, ValueError):
            pass

        self._schedule_flush()
        self._flush_greenlet.join(timeout=self.close_timeout)
        if not self._flush_greenlet.ready():
            logger.warning(
                "Datadog metrics flush exceeded %.1f seconds; "
                "continuing test shutdown with unsent telemetry.",
                self.close_timeout,
            )
            self._flush_greenlet.kill(block=False)

    def on_request(
        self,
        request_type,
        name,
        response_time,
        response_length,
        response,
        context,
        exception,
        **_kwargs,
    ):
        """Report each Locust request event to Datadog."""
        try:
            status_code = getattr(response, "status_code", None)
            if status_code is None:
                status_code = getattr(response, "status", None)
            timestamp = self._unix_timestamp()
            request_tags = {
                "name": name,
                "request_type": request_type,
                "environment": getattr(self.environment, "host", None),
            }
            if status_code is not None:
                request_tags["code"] = str(status_code)

            tags = self._merge_tags(request_tags)
            self.increment("locust_requests.count", tags=tags, timestamp=timestamp)
            self.gauge(
                "locust_requests.response_time",
                response_time,
                tags=tags,
                timestamp=timestamp,
            )
            if response_length is not None:
                self.gauge(
                    "locust_requests.response_length",
                    response_length,
                    tags=tags,
                    timestamp=timestamp,
                )
            if exception is not None:
                error_tags = tags | {"exception_type": type(exception).__name__}
                self.increment(
                    "locust_requests.error",
                    tags=error_tags,
                    timestamp=timestamp,
                )
        except Exception as exc:
            logger.warning("Failed to buffer Datadog request metrics: %s", exc)

    def record_check(
        self, check_name: str, check_passed: bool, extra_tags: dict, time=None
    ):
        """Report a check outcome."""
        timestamp = self._unix_timestamp(time)
        tags = self._merge_tags(extra_tags)
        tags.update(
            {
                "check_name": re.sub(
                    r"_+", "_", re.sub(r"[^a-z0-9]+", "_", check_name.lower())
                ).strip("_"),
                "environment": getattr(self.environment, "host", None),
            }
        )
        self.increment("locust_checks.total", tags=tags, timestamp=timestamp)
        metric_suffix = "passed" if check_passed else "failed"
        self.increment(
            f"locust_checks.{metric_suffix}",
            tags=tags,
            timestamp=timestamp,
        )

    def write_point(
        self, measurement: str, fields: dict, time=None, tags: dict | None = None
    ):
        """Report a custom point by expanding its numeric fields into metrics."""
        timestamp = self._unix_timestamp(time)
        merged_tags = self._merge_tags(tags or {})
        for field_name, value in fields.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                self.gauge(
                    f"{measurement}.{field_name}",
                    value,
                    tags=merged_tags,
                    timestamp=timestamp,
                )

    def increment(
        self,
        metric_name: str,
        value: int = 1,
        tags: dict | None = None,
        timestamp: int | None = None,
    ):
        """Buffer a count metric for Datadog."""
        self._buffer_metric(metric_name, value, "count", tags, timestamp)

    def gauge(
        self,
        metric_name: str,
        value: float,
        tags: dict | None = None,
        timestamp: int | None = None,
    ):
        """Buffer a gauge metric for Datadog."""
        self._buffer_metric(metric_name, value, "gauge", tags, timestamp)

    def _buffer_metric(
        self,
        metric_name: str,
        value: int | float,
        metric_type: str,
        tags: dict | None = None,
        timestamp: int | None = None,
    ):
        metric_path = (
            f"{self.namespace}.{metric_name}" if self.namespace else metric_name
        )
        self.series_buffer.append(
            {
                "metric": metric_path,
                "type": metric_type,
                "points": [[timestamp or self._unix_timestamp(), value]],
                "tags": self._format_tags(tags or {}),
            }
        )
        if len(self.series_buffer) >= self.batch_size:
            self._schedule_flush()

    def _schedule_flush(self):
        """Run Datadog HTTP I/O outside the Locust request path."""
        if self._flush_greenlet is None or self._flush_greenlet.ready():
            self._flush_greenlet = gevent.spawn(self.flush)

    def flush(self):
        """Flush buffered metrics to the Datadog API in batches."""
        while self.series_buffer:
            batch = self.series_buffer[: self.batch_size]
            del self.series_buffer[: self.batch_size]
            self._submit_series(batch)

    def _submit_series(self, series_batch: list[dict]):
        payload = json.dumps({"series": series_batch}).encode("utf-8")
        url = f"https://api.{self.site}/api/v1/series"
        api_request = request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "DD-API-KEY": self.api_key,
            },
            method="POST",
        )
        try:
            with request.urlopen(api_request, timeout=15) as response:
                response.read()
                logger.info(
                    "Submitted %s Datadog metric series to `%s`.",
                    len(series_batch),
                    self.site,
                )
        except error.HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")
            logger.warning(
                "Datadog metrics submission failed with HTTP %s for `%s`: %s",
                exc.code,
                self.site,
                response_body,
            )
        except Exception as exc:
            logger.warning(
                "Failed to submit Datadog metrics batch to `%s`: %s",
                self.site,
                exc,
            )

    def _merge_tags(self, tags: dict, extra_tags: dict | None = None) -> dict:
        merged_tags = self.default_tags.copy()
        merged_tags.update(tags)
        if extra_tags:
            merged_tags.update(extra_tags)
        return merged_tags

    @classmethod
    def _format_tags(cls, tags: dict) -> list[str]:
        formatted_tags = []
        for key, value in tags.items():
            if value is None or cls._is_volatile_or_sensitive_tag(key):
                continue
            normalized_key = str(key).replace(" ", "_")
            normalized_value = str(value).replace(" ", "_")
            formatted_tags.append(f"{normalized_key}:{normalized_value}")
        return formatted_tags

    @classmethod
    def _is_volatile_or_sensitive_tag(cls, key) -> bool:
        """Keep Datadog tags low-cardinality and free of obvious secrets."""
        normalized_key = str(key).strip().lower().replace("-", "_")
        return normalized_key.endswith("_id") or normalized_key in {
            "authorization",
            "cookie",
            "password",
            "secret",
            "token",
            "workspace_token",
        }

    @staticmethod
    def _unix_timestamp(metric_time=None) -> int:
        timestamp_source = metric_time or datetime.now(timezone.utc)
        if isinstance(timestamp_source, datetime):
            if timestamp_source.tzinfo is None:
                timestamp_source = timestamp_source.replace(tzinfo=timezone.utc)
            return int(timestamp_source.timestamp())
        return int(timestamp_source)


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
            try:
                self.datadog_listener = DatadogApiListener(
                    environment=environment,
                    **datadog_configuration,
                )
            except Exception as exc:
                logger.warning(
                    "Datadog listener initialization failed; "
                    "continuing without Datadog metrics: %s",
                    exc,
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
        except Exception as e:
            logger.warning(
                f"Unexpected exception appending trend data to environment object: {e}"
            )
        try:
            self._append_checks_data(environment)
        except Exception as e:
            logger.warning(
                f"Unexpected exception appending trend data to environment object: {e}"
            )
        if self.datadog_listener is not None:
            try:
                self.datadog_listener.close()
            except Exception as exc:
                logger.warning(
                    "Datadog metrics shutdown failed; continuing test shutdown: %s",
                    exc,
                )

    def flush_check_to_dbs(self, check_name: str, check_passed: bool, extra_tags: dict):
        """Flush a check datapoint to whatever grasshopper dbs are being used."""
        environment_base_url = self.locust_environment.host
        tags = {"check_name": check_name, "environment": environment_base_url}
        if hasattr(self.locust_environment, "extra_context"):
            tags.update(self.locust_environment.extra_context)
        tags.update(extra_tags)
        fields = {"check_passed": int(check_passed)}
        time = datetime.utcnow()

        if getattr(self, "influxdb_listener") is not None:
            point = self.influxdb_listener._InfluxDBListener__make_data_point(
                "locust_checks", fields, time, tags=tags
            )
            self.influxdb_listener.cache.append(point)
        if getattr(self, "datadog_listener") is not None:
            try:
                self.datadog_listener.record_check(
                    check_name=check_name,
                    check_passed=check_passed,
                    extra_tags=tags,
                    time=time,
                )
            except Exception as exc:
                logger.warning("Failed to buffer Datadog check metric: %s", exc)

    def write_metric_point(
        self, measurement: str, fields: dict, time=None, tags: dict | None = None
    ):
        """Write a custom point to every configured metrics backend."""
        metric_tags = tags or {}

        if getattr(self, "influxdb_listener") is not None:
            point = self.influxdb_listener._InfluxDBListener__make_data_point(
                measurement, fields, time or datetime.utcnow(), tags=metric_tags
            )
            self.influxdb_listener.cache.append(point)

        if getattr(self, "datadog_listener") is not None:
            try:
                self.datadog_listener.write_point(
                    measurement=measurement,
                    fields=fields,
                    time=time,
                    tags=metric_tags,
                )
            except Exception as exc:
                logger.warning("Failed to buffer Datadog custom metric: %s", exc)

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
            logger.info("No checks data to report.")
