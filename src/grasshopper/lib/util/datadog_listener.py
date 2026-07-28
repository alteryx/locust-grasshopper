"""Datadog metrics listener."""

import json
import logging
import re
from datetime import datetime, timezone
from urllib import error, request

import gevent
from locust.env import Environment

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
        """Register the listener and keep Datadog API settings.

        Metrics are cached until `batch_size` series are ready, then submitted from a
        gevent greenlet so Datadog network I/O does not slow Locust request handling.
        `close_timeout` caps the best-effort shutdown flush.
        """
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

        if not self.series_buffer:
            return

        self._schedule_flush()
        if self._flush_greenlet is None:
            return
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
        """Convert a Locust request event into Datadog request metrics."""
        status_code = getattr(response, "status_code", None)
        timestamp = self._unix_timestamp()
        tags = self.default_tags | {
            "name": name,
            "request_type": request_type,
            "environment": getattr(self.environment, "host", None),
            "code": str(status_code) if status_code is not None else None,
        }

        self._buffer_metric("locust_requests.count", 1, "count", tags, timestamp)
        self._buffer_metric(
            "locust_requests.response_time", response_time, "gauge", tags, timestamp
        )
        if response_length is not None:
            self._buffer_metric(
                "locust_requests.response_length",
                response_length,
                "gauge",
                tags,
                timestamp,
            )
        if exception is not None:
            self._buffer_metric(
                "locust_requests.error",
                1,
                "count",
                tags | {"exception_type": type(exception).__name__},
                timestamp,
            )

    def record_check(
        self, check_name: str, check_passed: bool, extra_tags: dict, time=None
    ):
        """Record total and pass/fail count metrics for one Grasshopper check."""
        timestamp = self._unix_timestamp(time)
        tags = (
            self.default_tags
            | extra_tags
            | {
                "check_name": re.sub(
                    r"_+", "_", re.sub(r"[^a-z0-9]+", "_", check_name.lower())
                ).strip("_"),
                "environment": getattr(self.environment, "host", None),
            }
        )
        self._buffer_metric("locust_checks.total", 1, "count", tags, timestamp)
        metric_suffix = "passed" if check_passed else "failed"
        self._buffer_metric(
            f"locust_checks.{metric_suffix}", 1, "count", tags, timestamp
        )

    def record_custom_point(
        self, measurement: str, fields: dict, time=None, tags: dict | None = None
    ):
        """Record numeric custom fields as Datadog gauge metrics."""
        timestamp = self._unix_timestamp(time)
        metric_tags = self.default_tags | (tags or {})
        for field_name, value in fields.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                self._buffer_metric(
                    f"{measurement}.{field_name}",
                    value,
                    "gauge",
                    metric_tags,
                    timestamp,
                )

    def _buffer_metric(
        self,
        metric_name: str,
        value: float,
        metric_type: str,
        tags: dict,
        timestamp: int | None = None,
    ):
        """Append one Datadog series payload and flush when the batch is full."""
        metric_path = (
            f"{self.namespace}.{metric_name}" if self.namespace else metric_name
        )
        self.series_buffer.append(
            {
                "metric": metric_path,
                "type": metric_type,
                "points": [[timestamp or self._unix_timestamp(), value]],
                "tags": [
                    f"{key}:{value}" for key, value in tags.items() if value is not None
                ],
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
        """Submit one already-built Datadog series batch."""
        payload = json.dumps({"series": series_batch}).encode("utf-8")
        api_request = request.Request(
            f"https://api.{self.site}/api/v1/series",
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
            logger.warning(
                "Datadog metrics submission failed with HTTP %s for `%s`: %s",
                exc.code,
                self.site,
                exc.read().decode("utf-8", errors="replace"),
            )
        except (OSError, TimeoutError, error.URLError) as exc:
            logger.warning(
                "Failed to submit Datadog metrics batch to `%s`: %s",
                self.site,
                exc,
            )

    @staticmethod
    def _unix_timestamp(metric_time=None) -> int:
        """Return Datadog-compatible Unix seconds for a metric point."""
        timestamp_source = metric_time or datetime.now(timezone.utc)
        if isinstance(timestamp_source, datetime):
            if timestamp_source.tzinfo is None:
                timestamp_source = timestamp_source.replace(tzinfo=timezone.utc)
            return int(timestamp_source.timestamp())
        return int(timestamp_source)
