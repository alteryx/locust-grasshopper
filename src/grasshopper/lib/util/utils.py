"""Module: Utils.

These are the miscellaneous utility functions for the project that couldn't find
another place to live.
"""

import logging
import sys
import time
from datetime import datetime

from termcolor import colored

from grasshopper.lib.util.check_constants import CheckConstants

logger = logging.getLogger()


def custom_trend(trend_name: str, extra_tag_keys=[]):
    """Establish a custom trend for a function."""

    def calc_time_delta_and_report_metric(func):
        def wrapper(journey_object, *args, **kwargs):
            tags = {}
            try:
                environment = journey_object.environment
                host = environment.host
                test_parameters = journey_object.scenario_args
                if hasattr(journey_object.environment, "extra_context"):
                    tags.update(journey_object.environment.extra_context)
            except AttributeError:
                raise ReferenceError(
                    "The custom_trend decorator must be placed on a journey function "
                    "which has a test parameters and host attributes defined."
                )

            start_time = datetime.now()
            result = func(journey_object, *args, **kwargs)
            end_time = datetime.now()
            time_delta = end_time - start_time
            tags.update(
                {
                    extra_tag_key: test_parameters.get(extra_tag_key)
                    for extra_tag_key in extra_tag_keys
                }
            )
            tags["environment"] = host
            environment.events.request.fire(
                request_type="CUSTOM",
                name=trend_name,
                response_time=round(time_delta.total_seconds() * 1000, 3),
                response_length=0,
                response=None,
                context=tags,
                exception=None,
            )
            return result

        return wrapper

    return calc_time_delta_and_report_metric


def current_method_name():
    """Get the name of the current method."""
    return sys._getframe(1).f_code.co_name


def highlight_print(text: str):
    """Print a string in bold with a highlighted color."""
    ctext = colored(text, "green", attrs=["bold"])
    logger.info(ctext)


def check(
    check_name: str,
    check_is_good: bool,
    env,
    tags={},
    halt_on_failure=False,
    msg_on_failure=None,
    flexible_warning=0.95,
):
    """
    Do a soft assertion on some condition.

    Required parameters:
    - check_name: A name for the check
    - check_is_good: A boolean expression that resolves to a boolean value
      (example: request.body.data[0] == 1)
    - env: The environment object (should be 'self.environment' in the locustfile)

    Optional parameters:
    - tags: an optional dictionary to add to timeseries metrics
    - halt_on_failure: if set to True, stops test on a fail. Set to False by default
    - flexible_warning: sets a threshold for whether the output is red or yellow.
    (example 1: flexible_warning of 0.5, and 3/5 checks pass, output is yellow.)
    (example 2: flexible_warning of 0.95, and 92/100 checks pass, output is red.)

    TODO: this whole thing needs to be re-worked because we are calculating the
    passing threshold in more than one place, some of which is in the slack formatter
    plus the checks functionality should probably be it's own class instead of being
    spread out across a couple of different locations
    TODO: look at creating a checks class after the Grasshopper class has been merged

    For now, we know that the slack formatter and report portal may sometimes have
    slightly different calculations.

    """
    check_is_good = bool(check_is_good)
    check_object = {
        "passed": 0,
        "failed": 0,
        "total": 0,
        "warning_threshold": flexible_warning,
    }

    if hasattr(env.stats, "checks") and type(env.stats.checks) is dict:
        if check_name not in env.stats.checks.keys():
            env.stats.checks[check_name] = check_object
    else:
        env.stats.checks = {check_name: check_object}

    if hasattr(env, "grasshopper_listeners"):
        env.grasshopper_listeners.flush_check_to_dbs(
            check_name=check_name, check_passed=check_is_good, extra_tags=tags
        )
    checks = env.stats.checks
    checks[check_name]["total"] += 1

    if check_is_good:
        checks[check_name]["passed"] += 1
    else:
        checks[check_name]["failed"] += 1
        logger.warning(f"Check failed: {check_name}")
        if msg_on_failure:
            logger.warning(f"Failure message: {msg_on_failure}")
        if halt_on_failure:
            logger.fatal("Check failed with halt_on_failure enabled. Stopping runner")
            env.runner.quit()


def report_thresholds_to_console(trend_dict):
    """Print all the thresholds to the console in a pretty table."""
    length = 32
    logger.info("-" * length + " THRESHOLD REPORT " + "-" * length)
    logger.info(
        "{:<45} {:<10} {:<10} {:<10}".format(
            "Trend_Name", "Percentile", "Limit", "Actual"
        )
    )
    for trend_name, trend_values in trend_dict.items():
        if "thresholds" in trend_values:
            for threshold_item in trend_values["thresholds"]:
                formatted_result_string = "{:<45} {:<10} {:<10} {:<10}".format(
                    trend_name,
                    int(threshold_item["percentile"] * 100),
                    f'{threshold_item["less_than_in_ms"]}ms',
                    f'{int(threshold_item["actual_value_in_ms"])}ms',
                )
                if threshold_item["succeeded"]:
                    logger.info(
                        colored(formatted_result_string, "green", attrs=["bold"])
                    )
                else:
                    logger.info(colored(formatted_result_string, "red", attrs=["bold"]))
    logger.info("-" * 82)


def report_checks_to_console(checks_dict):
    """Print all the checks to the console in a pretty table."""
    color_map = {
        CheckConstants.VERDICT_ALL_PASSED: "green",
        CheckConstants.VERDICT_PASSED_RATE_OVER_THRESHOLD: "yellow",
        CheckConstants.VERDICT_FAILED: "red",
    }
    length = 55
    logger.info("-" * length + " CHECKS REPORT " + "-" * length)
    logger.info(
        "{:<80} {:<10} {:<10} {:<10} {:<10}".format(
            "Check_Name", "Passed", "Failed", "Total", "Percentage"
        )
    )
    for check_key, check_value in checks_dict.items():
        passed, failed, total, percent = (
            check_value["passed"],
            check_value["failed"],
            check_value["total"],
            check_value["percentage_passed_display"],
        )
        result_string = "{:<80} {:<10} {:<10} {:<10} {:<10}".format(
            check_key, passed, failed, total, percent
        )
        color_to_print = color_map.get(check_value["verdict"]) or "white"
        logger.info(colored(result_string, color_to_print, attrs=["bold"]))
    logger.info("-" * 125)


def epoch_time():
    """Return the epoch time for the current moment ('now').

    This is a convenience method, to avoid having to look up the calculation
    of epoch time. It's also fine if you don't use it, it's not something I
    imagine will change, like ever.
    """
    return int(time.time() * 1000)
