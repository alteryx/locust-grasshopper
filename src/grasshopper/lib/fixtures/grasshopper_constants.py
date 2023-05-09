"""The file for the GrasshopperConstants class."""


class GrasshopperConstants:
    """Things that are always the same in grasshopper tests."""

    GRASSHOPPER_ATTR_NAMES = [
        "runtime",
        "users",
        "spawn_rate",
        "shape",
        "scenario_file",
        "scenario_name",
        "tags",
        "influxdb",  # legacy influx_host arg
        "influx_host",
        "influx_port",
        "influx_user",
        "influx_pwd",
        "shape_instance",
        "scenario_delay",
        "slack_webhook",
        "slack_report_failures_only",
        "cleanup_s3",
        "rp_token",
        "rp_launch_name",
        "rp_project",
        "rp_endpoint",
    ]
    RUNTIME_DEFAULT = 120.0
    USERS_DEFAULT = 1
    SPAWN_RATE_DEFAULT = 1.0
    SHAPE_DEFAULT = "Default"
    SCENARIO_DELAY_DEFAULT = 0.0
    THRESHOLD_PERCENTILE_DEFAULT = 0.9
