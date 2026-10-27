"""Module: Utils.

These are the miscellaneous utility functions for the project that couldn't find
another place to live.
"""

import logging
import sys
import time
from datetime import datetime
from typing import Any

from grasshopper.lib.util.check_constants import CheckConstants
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text
from termcolor import colored

logger = logging.getLogger()


def custom_trend(trend_name: str, extra_tag_keys=[]):
    """Establish a custom trend for a function."""

    def calc_time_delta_and_report_metric(func):
        def wrapper(journey_object, *args, **kwargs):
            try:
                environment = journey_object.environment
            except AttributeError:
                raise ReferenceError(
                    "The custom_trend decorator must be placed on a journey function "
                    "which has a test parameters and host attributes defined."
                )

            start_time = datetime.now()
            result = func(journey_object, *args, **kwargs)
            end_time = datetime.now()
            time_delta = end_time - start_time
            environment.events.request.fire(
                request_type="CUSTOM",
                name=trend_name,
                response_time=round(time_delta.total_seconds() * 1000, 3),
                response_length=0,
                response=None,
                context=journey_object.tags,
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


class _ConsoleReport:
    """Render when a log handler emits, after pytest restores terminal output."""

    def __init__(self, table: Table) -> None:
        self.table = table

    def __str__(self) -> str:
        console = Console(file=sys.__stdout__)
        with console.capture() as capture:
            console.print(self.table)
        return capture.get().rstrip()


def _log_report(table: Table) -> None:
    """Keep each report together and defer color detection until log emission."""
    logger.info("\n%s", _ConsoleReport(table))


def report_thresholds_to_console(trend_dict: dict[str, dict[str, Any]]) -> None:
    """Report timing budgets and explicit pass/fail results."""
    table = Table(title="Timing thresholds", box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Trend")
    table.add_column("Type")
    for heading in ("Percentile", "Limit", "Actual"):
        table.add_column(heading, justify="right")
    table.add_column("Result")
    for trend_name, trend_values in trend_dict.items():
        for threshold in trend_values.get("thresholds", []):
            passed = threshold["succeeded"]
            table.add_row(
                Text(trend_name),
                Text(threshold["http_method"]),
                f"{threshold['percentile'] * 100:g}%",
                f"{threshold['less_than_in_ms']:g} ms",
                f"{threshold['actual_value_in_ms']:g} ms",
                Text(
                    "PASS" if passed else "FAIL",
                    style="bold green" if passed else "bold red",
                ),
            )
    _log_report(table)


def report_checks_to_console(checks_dict: dict[str, dict[str, Any]]) -> None:
    """Report named checks with counts, pass rates, and readable verdicts."""
    verdicts = {
        CheckConstants.VERDICT_ALL_PASSED: ("PASS", "bold green"),
        CheckConstants.VERDICT_PASSED_RATE_OVER_THRESHOLD: ("WARN", "bold yellow"),
        CheckConstants.VERDICT_FAILED: ("FAIL", "bold red"),
    }
    table = Table(title="Named checks", box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Check")
    for heading in ("Passed", "Failed", "Total", "Pass rate"):
        table.add_column(heading, justify="right")
    table.add_column("Result")
    for name, check_result in checks_dict.items():
        verdict, style = verdicts.get(check_result["verdict"], ("UNKNOWN", "dim"))
        percent = str(check_result["percentage_passed_display"]).rstrip("%")
        table.add_row(
            Text(name),
            str(check_result["passed"]),
            str(check_result["failed"]),
            str(check_result["total"]),
            f"{percent}%",
            Text(verdict, style=style),
        )
    _log_report(table)


def epoch_time():
    """Return the epoch time for the current moment ('now').

    This is a convenience method, to avoid having to look up the calculation
    of epoch time. It's also fine if you don't use it, it's not something I
    imagine will change, like ever.
    """
    return int(time.time() * 1000)
