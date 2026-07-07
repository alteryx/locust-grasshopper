from grasshopper.lib.grasshopper import Grasshopper


def test_datadog_configuration_from_global_configuration(monkeypatch):
    monkeypatch.delenv("DD_AGENT_HOST", raising=False)
    monkeypatch.delenv("DD_API_KEY", raising=False)
    monkeypatch.delenv("DD_SITE", raising=False)
    monkeypatch.delenv("DD_ENV", raising=False)
    monkeypatch.delenv("DD_SERVICE", raising=False)

    grasshopper = Grasshopper(
        {
            "datadog_api_key": "secret",
            "datadog_site": "us5.datadoghq.com",
            "datadog_namespace": "perf",
            "datadog_env": "test",
            "datadog_service": "shield-trifacta",
            "datadog_tags": "team:shield,test:navigation",
        }
    )

    assert grasshopper.datadog_configuration == {
        "api_key": "secret",
        "site": "us5.datadoghq.com",
        "namespace": "perf",
        "default_tags": {
            "env": "test",
            "service": "shield-trifacta",
            "team": "shield",
            "test": "navigation",
        },
    }


def test_datadog_configuration_falls_back_to_dd_env_vars(monkeypatch):
    monkeypatch.setenv("DD_API_KEY", "secret-from-env")
    monkeypatch.setenv("DD_SITE", "datadoghq.eu")
    monkeypatch.setenv("DD_ENV", "sandbox")
    monkeypatch.setenv("DD_SERVICE", "grasshopper")
    monkeypatch.setenv("DD_TAGS", "team:whiskyx,test:navigation")

    grasshopper = Grasshopper({})

    assert grasshopper.datadog_configuration == {
        "api_key": "secret-from-env",
        "site": "datadoghq.eu",
        "namespace": "grasshopper",
        "default_tags": {
            "env": "sandbox",
            "service": "grasshopper",
            "team": "whiskyx",
            "test": "navigation",
        },
    }


def test_parse_datadog_tags_supports_flag_style_tags():
    assert Grasshopper._parse_datadog_tags("team:shield,smoke") == {
        "team": "shield",
        "smoke": "true",
    }
