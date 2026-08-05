from unittest.mock import MagicMock

import pytest
from grasshopper.lib.grasshopper import Grasshopper
from grasshopper.lib.util.datadog_listener import DatadogApiListener
from grasshopper.lib.util.listeners import GrasshopperListeners


def test_datadog_configuration_uses_standard_environment_variables(monkeypatch):
    monkeypatch.setenv("DD_API_KEY", "secret-from-env")
    monkeypatch.setenv("DD_SITE", "datadoghq.eu")
    monkeypatch.setenv("DD_ENV", "sandbox")
    monkeypatch.setenv("DD_SERVICE", "grasshopper")
    monkeypatch.setenv("DD_VERSION", "abc123")

    grasshopper = Grasshopper({})

    assert grasshopper.datadog_configuration == {
        "api_key": "secret-from-env",
        "site": "datadoghq.eu",
        "namespace": "grasshopper",
        "default_tags": {
            "env": "sandbox",
            "service": "grasshopper",
            "version": "abc123",
        },
    }


@pytest.mark.parametrize("missing_variable", ["DD_API_KEY", "DD_ENV"])
def test_datadog_configuration_requires_api_key_and_environment(
    monkeypatch, missing_variable
):
    monkeypatch.setenv("DD_API_KEY", "secret-from-env")
    monkeypatch.setenv("DD_ENV", "sandbox")
    monkeypatch.delenv(missing_variable)

    assert Grasshopper({}).datadog_configuration == {}


def test_datadog_listener_emits_request_metrics(monkeypatch):
    env = MagicMock()
    env.host = "https://perf.example"
    response_mock = MagicMock()
    response_mock.read.return_value = b"{}"
    response_mock.__enter__.return_value = response_mock
    response_mock.__exit__.return_value = None
    urlopen_mock = MagicMock(return_value=response_mock)
    monkeypatch.setattr(
        "grasshopper.lib.util.datadog_listener.request.urlopen", urlopen_mock
    )

    listener = DatadogApiListener(
        environment=env,
        api_key="secret",
        site="datadoghq.com",
        namespace="grasshopper",
        default_tags={"service": "shield-trifacta"},
    )
    listener.on_request(
        request_type="CUSTOM",
        name="PX_TREND_example",
        response_time=123.4,
        response_length=0,
        response=MagicMock(status_code=201),
        context={
            "journey": "example",
            "job_id": "job-123",
            "workspace_token": "do-not-emit",
        },
        exception=None,
    )
    listener.flush()

    request_obj = urlopen_mock.call_args.args[0]
    assert request_obj.full_url == "https://api.datadoghq.com/api/v1/series"
    assert request_obj.headers["Dd-api-key"] == "secret"
    payload = request_obj.data.decode("utf-8")
    assert '"metric": "grasshopper.locust_requests.count"' in payload
    assert '"metric": "grasshopper.locust_requests.response_time"' in payload
    assert '"service:shield-trifacta"' in payload
    assert '"code:201"' in payload
    assert "journey:example" not in payload
    assert "job-123" not in payload
    assert "do-not-emit" not in payload


def test_datadog_check_name_matches_trace_correlation_format():
    env = MagicMock()
    env.host = "https://perf.example"
    listener = DatadogApiListener(environment=env, api_key="secret")

    listener.record_check(
        "WorkflowCriticalUserJourney | Workflow deleted",
        True,
        {"check_name": "untrusted override"},
    )

    assert len(listener.series_buffer) == 2
    for metric in listener.series_buffer:
        assert (
            "check_name:workflowcriticaluserjourney_workflow_deleted" in metric["tags"]
        )


def test_datadog_listener_schedules_network_flush_off_request_path(monkeypatch):
    env = MagicMock()
    scheduled = []
    monkeypatch.setattr(
        "grasshopper.lib.util.datadog_listener.gevent.spawn",
        lambda func: scheduled.append(func) or MagicMock(),
    )
    listener = DatadogApiListener(
        environment=env,
        api_key="secret",
        batch_size=1,
    )

    listener.record_custom_point("measurement", {"metric": 1})

    assert scheduled == [listener.flush]


def test_grasshopper_listeners_leave_datadog_disabled_without_api_key():
    env = MagicMock()
    env.grasshopper.influx_configuration = {"influx_host": None}
    env.grasshopper.datadog_configuration = {
        "site": "datadoghq.com",
        "namespace": "grasshopper",
    }
    listeners = GrasshopperListeners(environment=env)

    listeners.on_test_start(env)

    assert listeners.datadog_listener is None


def test_write_metric_point_reports_to_datadog_listener():
    env = MagicMock()
    listeners = GrasshopperListeners(environment=env)
    listeners.datadog_listener = MagicMock()
    timestamp = MagicMock()

    listeners.write_metric_point(
        "locust_requests",
        {"response_time": 456.0},
        time=timestamp,
        tags={"job_type": "batch"},
    )

    listeners.datadog_listener.record_custom_point.assert_called_once_with(
        measurement="locust_requests",
        fields={"response_time": 456.0},
        time=timestamp,
        tags={"job_type": "batch"},
    )


def test_flush_check_to_dbs_reports_merged_tags_to_datadog_listener():
    env = MagicMock()
    env.host = "https://perf.example"
    env.extra_context = {"journey": "connections"}
    listeners = GrasshopperListeners(environment=env)
    listeners.datadog_listener = MagicMock()

    listeners.flush_check_to_dbs(
        "connection health",
        True,
        {"job_type": "batch"},
    )

    listeners.datadog_listener.record_check.assert_called_once()
    call_kwargs = listeners.datadog_listener.record_check.call_args.kwargs
    assert call_kwargs["check_name"] == "connection health"
    assert call_kwargs["check_passed"] is True
    assert call_kwargs["extra_tags"] == {
        "check_name": "connection health",
        "environment": "https://perf.example",
        "journey": "connections",
        "job_type": "batch",
    }
