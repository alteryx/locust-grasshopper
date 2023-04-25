"""Module: GHConfiguration.

Code to support loading grasshopper configuration values:
+ Store information about the grasshopper configuration values
+ Class to carry configuration values (subclass of dict)
+ Code for managing the loading process

"""
import json
import logging

logger = logging.getLogger(__name__)


def typecast_dict(value):
    """Ensure that value is a dict (supports json strings) or log a warning."""
    new_value = value
    if type(value) == str:
        new_value = json.loads(value)
    elif type(value) != dict:
        logger.warning(
            f"Configuration value [{value}] of type [{type(value)}] not able to be "
            f"cast to dictionary."
        )

    return new_value


def typecast_int(value):
    """Ensure value is an int or raise an error."""
    new_value = int(value)
    return new_value


def typecast_float(value):
    """Ensure value is a float or raise an error."""
    new_value = float(value)
    return new_value


def typecast_bool(value):
    """Ensure value is a bool or raise an error."""
    if type(value) == str:
        new_value = value.lower() in ["true"]
    else:
        new_value = bool(value)

    return new_value


class ConfigurationConstants:
    """Class to hold the _definition_ of all the configuration values available.

    Different categories for the attrs are mainly to make it easier to understand the
    effect and use of the different values. And to keep it kinda organized.

    """

    # Grasshopper attrs that are typically set per test location (e.g. test repo)
    GRASSHOPPER_ATTRS = {
        "influx_host": {
            "opts": ["--influx_host"],
            "attrs": {
                "action": "store",
                "help": "Influx host ip address.",
            },
        },
        "influxdb": {  # TODO-DEPRECATED, USE INFLUX_HOST INSTEAD
            "opts": ["--influxdb"],
            "attrs": {
                "action": "store",
                "help": "Legacy argument name for influx_host.",
            },
        },
        "influx_port": {
            "opts": ["--influx_port"],
            "attrs": {
                "action": "store",
                "help": "Influx port for specified host.",
            },
        },
        "influx_user": {
            "opts": ["--influx_user"],
            "attrs": {
                "action": "store",
                "help": "Username to connect to the influx host.",
            },
        },
        "influx_pwd": {
            "opts": ["--influx_pwd"],
            "attrs": {
                "action": "store",
                "type": str,
                "help": "Password to connect to the influx host.",
            },
        },
        "slack_webhook": {
            "opts": ["--slack_webhook"],
            "attrs": {
                "action": "store",
                "type": str,
                "help": "Url of specified slack channel webhook. NYI.",
            },
        },
        "slack_report_failures_only": {
            "opts": ["--slack_report_failures_only"],
            "attrs": {
                "action": "store",
                "type": bool,
                "help": "True to only post to slack for a scenario when there are "
                "failures in either the thresholds or checks.",
            },
            "typecast": typecast_bool,
            "default": False,
        },
        "rp_token": {
            "opts": ["--rp_token"],
            "attrs": {
                "action": "store",
                "help": "API token for accessing report portal server. NYI. "
                "programmatically.",
            },
        },
        "rp_project": {
            "opts": ["--rp_project"],
            "attrs": {
                "action": "store",
                "help": "Project ID for report portal project. NYI.",
            },
        },
        "rp_endpoint": {
            "opts": ["--rp_endpoint"],
            "attrs": {
                "action": "store",
                "help": "API endpoint for the report portal server. NYI.",
            },
        },
    }

    # Testrun attrs are typically set per test run and may change every time you
    # perform a different test run
    TESTRUN_ATTRS = {
        "shape": {
            "opts": ["-S", "--shape"],
            "attrs": {
                "action": "store",
                "type": str,
                "help": "Name of a shape class to use, Default shape is used if "
                "nothing is specified.",
            },
            "default": "Default",
        },
        "spawn_instance": {
            "opts": ["--spawn_instance"],
            "attrs": {
                "action": "store",
                "help": "Shape instance, used only by the scenario collector.",
            },
        },
        "users": {
            "opts": ["-U", "--users"],
            "attrs": {
                "action": "store",
                "type": int,
                "help": "Target number of users.",
            },
            "default": 1.0,
            "typecast": typecast_int,
        },
        "runtime": {
            "opts": ["--runtime"],
            "attrs": {
                "action": "store",
                "type": float,
                "help": "Runtime per scenario in milliseconds.",
            },
            "default": 120.0,
            "typecast": typecast_float,
        },
        "spawn_rate": {
            "opts": ["-R", "--spawn_rate"],
            "attrs": {
                "action": "store",
                "type": float,
                "help": "Rate at which new users are added, as expressed in "
                "users/second.",
            },
            "default": 1.0,
            "typecast": typecast_float,
        },
        "scenario_file": {
            "opts": ["--scenario_file"],
            "attrs": {
                "action": "store",
                "type": str,
                "help": "Path to a scenario yaml file.",
            },
        },
        "scenario_name": {
            "opts": ["--scenario_name"],
            "attrs": {
                "action": "store",
                "type": str,
                "help": "Name (key) for a single scenario in the specified yaml file.",
            },
        },
        "tags": {
            "opts": ["--tags"],
            "attrs": {
                "action": "store",
                "type": str,
                "help": "Tags to use for collection of scenarios from the specified "
                "yaml file.",
            },
        },
        "scenario_delay": {
            "opts": ["--scenario_delay"],
            "attrs": {
                "action": "store",
                "type": float,
                "help": "Delay between scenarios in seconds.",
            },
            "default": 0.0,
            "typecast": typecast_float,
        },
        "cleanup_s3": {
            "opts": ["--cleanup_s3"],
            "attrs": {
                "action": "store",
                "type": bool,
                "help": "True to execute the cleanup s3 fixture.",
            },
            "default": True,
            "typecast": typecast_bool,
        },
        "slack": {
            "opts": ["--slack"],
            "attrs": {
                "action": "store",
                "help": "True to post to slack. NYI.",
            },
            "default": False,
            "typecast": typecast_bool,
        },
        "influx": {
            "opts": ["--influx"],
            "attrs": {
                "action": "store",
                "type": bool,
                "help": "True to post to specified influx host. NYI.",
            },
            "typecast": typecast_bool,
            "default": False,
        },
        "report_portal": {
            "opts": ["--report_portal"],
            "attrs": {
                "action": "store",
                "type": bool,
                "help": "True to post results to report portal. NYI",
            },
            "typecast": typecast_bool,
            "default": False,
        },
        "rp_launch_name": {
            "opts": ["--rp_launch_name"],
            "attrs": {
                "action": "store",
                "help": "Base launch name to use when posting to report portal. NYI",
            },
            "default": "Grasshopper Performance Test Run | Launch name unknown",
        },
    }

    # Scenario attrs are typically set per scenario and usually are loaded from the
    # scenario definition in a yaml file; However we don't enumerate all the possible
    # values because that would be very hard to maintain. listed here are just the ones
    # that we need to pull from the yaml and do something with (e.g. typecast)
    SCENARIO_ATTRS = {
        "thresholds": {
            "opts": ["--thresholds"],
            "attrs": {
                "action": "store",
                "type": str,
                "help": "Thresholds",
            },
            "typecast": typecast_dict,
        }
    }

    COMPLETE_ATTRS = {**GRASSHOPPER_ATTRS, **TESTRUN_ATTRS, **SCENARIO_ATTRS}

    SHAPE_OVERRIDE_ATTR_NAMES = ["runtime", "spawn_rate", "users"]


class GHConfiguration(dict):
    """Collection to hold Grasshopper configuration values.

    This serves 2 purposes right now:
    1. it lets us identify if a given dict is a _configuration_ dict
    2. it is a place that we can add a few convenience operations on top of all the
    dict operations it inherits (more coming soon...)

    """

    def update_single_key(self, key, value):
        """Update a single key in the underlying dict, convenience method."""
        if value is not None:
            self[key] = value
