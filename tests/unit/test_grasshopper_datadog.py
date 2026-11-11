import json
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
    env.grasshopper.global_configuration = {"scenario_name": "workflow_cuj_spike_test"}
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
            "test_type": "load",
            "job_id": "job-123",
            "workspace_token": "do-not-emit",
        },
        exception=RuntimeError("request failed"),
    )
    listener.flush()

    requests = [call.args[0] for call in urlopen_mock.call_args_list]
    assert {request.full_url for request in requests} == {
        "https://api.datadoghq.com/api/v1/series",
        "https://api.datadoghq.com/api/v1/distribution_points",
    }
    for request_obj in requests:
        assert request_obj.headers["Dd-api-key"] == "secret"
    series_payload = next(
        request.data.decode("utf-8")
        for request in requests
        if request.full_url.endswith("/series")
    )
    distribution_payload = next(
        request.data.decode("utf-8")
        for request in requests
        if request.full_url.endswith("/distribution_points")
    )
    distribution_series = json.loads(distribution_payload)["series"]
    request_distribution = next(
        series
        for series in distribution_series
        if series["metric"] == "grasshopper.locust_requests.response_time_distribution"
    )
    assert '"metric": "grasshopper.locust_requests.count"' in series_payload
    assert '"metric": "grasshopper.locust_requests.response_time"' in series_payload
    assert (
        '"metric": "grasshopper.locust_requests.response_time_distribution"'
        in distribution_payload
    )
    assert '"metric": "grasshopper.locust_requests.error"' in series_payload
    assert '"type": "distribution"' in distribution_payload
    assert request_distribution["points"][0][1] == [123.4]
    assert '"service:shield-trifacta"' in series_payload
    assert '"code:201"' in series_payload
    assert '"cuj:workflow_cuj_spike_test"' in series_payload
    assert '"cuj:workflow_cuj_spike_test"' in distribution_payload
    assert '"test_type:load"' in series_payload
    assert "job-123" not in series_payload
    assert "do-not-emit" not in series_payload


def test_datadog_listener_uses_actual_request_name_tag():
    env = MagicMock()
    env.host = "https://perf.example"
    listener = DatadogApiListener(environment=env, api_key="secret")

    listener.on_request(
        request_type="GET",
        name="list_connections",
        response_time=10,
        response_length=0,
        response=MagicMock(status_code=200),
        context={},
        exception=None,
    )

    request_metric = next(
        metric
        for metric in listener.series_buffer
        if metric["metric"].endswith("locust_requests.count")
    )
    assert "name:list_connections" in request_metric["tags"]
    assert "request_name:list_connections" in request_metric["tags"]


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


def test_user_load_metrics_report_configured_and_terminal_active_values(monkeypatch):
    env = MagicMock()
    env.grasshopper.global_configuration = {
        "users": 10,
        "scenario_name": "workflow_cuj",
        "test_type": "load",
    }
    env.runner.user_count = 3
    listeners = GrasshopperListeners(environment=env)
    listeners.datadog_listener = MagicMock()
    greenlet = MagicMock()
    monkeypatch.setattr(
        "grasshopper.lib.util.listeners.gevent.spawn", lambda *args: greenlet
    )

    listeners._start_user_metrics(env)
    listeners._stop_user_metrics(env)

    calls = listeners.datadog_listener.record_custom_point.call_args_list
    assert calls[0].kwargs["measurement"] == "locust_users"
    assert calls[0].kwargs["fields"] == {"configured": 10}
    assert calls[0].kwargs["tags"] == {
        "cuj": "workflow_cuj",
        "test_type": "load",
        "scope": "environment",
    }
    assert calls[-1].kwargs["fields"] == {"active": 0}
    greenlet.kill.assert_called_once_with(block=False)


def test_user_load_metrics_omit_cuj_without_scenario_name(monkeypatch):
    env = MagicMock()
    env.grasshopper.global_configuration = {"users": 10, "test_type": "load"}
    env.runner.user_count = 3
    listeners = GrasshopperListeners(environment=env)
    listeners.datadog_listener = MagicMock()
    greenlet = MagicMock()
    monkeypatch.setattr(
        "grasshopper.lib.util.listeners.gevent.spawn", lambda *args: greenlet
    )

    listeners._start_user_metrics(env)

    assert listeners.datadog_listener.record_custom_point.call_args.kwargs["tags"] == {
        "test_type": "load",
        "scope": "environment",
    }


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


def test_flush_check_to_dbs_adds_scenario_cuj_only_to_datadog():
    env = MagicMock()
    env.host = "https://perf.example"
    env.grasshopper.global_configuration = {"scenario_name": "workflow_cuj_spike_test"}
    listeners = GrasshopperListeners(environment=env)
    listeners.datadog_listener = MagicMock()
    listeners.influxdb_listener = MagicMock()

    listeners.flush_check_to_dbs("workflow created", True, {})

    datadog_tags = listeners.datadog_listener.record_check.call_args.kwargs[
        "extra_tags"
    ]
    assert datadog_tags["cuj"] == "workflow_cuj_spike_test"
    influx_tags = listeners.influxdb_listener.cache.append.call_args.args[0]["tags"]
    assert "cuj" not in influx_tags


def test_flush_check_to_dbs_uses_scenario_name_for_cuj():
    env = MagicMock()
    env.host = "https://perf.example"
    env.grasshopper.global_configuration = {"scenario_name": "composite_scenario"}
    listeners = GrasshopperListeners(environment=env)
    listeners.datadog_listener = MagicMock()

    listeners.flush_check_to_dbs(
        "workflow created", True, {"cuj": "workflow_cuj_spike_test"}
    )

    datadog_tags = listeners.datadog_listener.record_check.call_args.kwargs[
        "extra_tags"
    ]
    assert datadog_tags["cuj"] == "composite_scenario"


def test_flush_check_to_dbs_omits_cuj_when_scenario_name_is_unavailable():
    env = MagicMock()
    env.host = "https://perf.example"
    env.grasshopper.global_configuration = {}
    listeners = GrasshopperListeners(environment=env)
    listeners.datadog_listener = MagicMock()

    listeners.flush_check_to_dbs(
        "workflow created", True, {"cuj": "should_not_be_used"}
    )

    datadog_tags = listeners.datadog_listener.record_check.call_args.kwargs[
        "extra_tags"
    ]
    assert "cuj" not in datadog_tags
