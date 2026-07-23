import pytest
from grasshopper.lib.grasshopper import Grasshopper


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
