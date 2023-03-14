"""Module: Shared Reporting.

Contains a variety of methods that are used by grasshopper provided extended reporters.
Also intended to be optionally used by ers that grasshopper consumers create.

"""
from typing import Any, Callable, Dict, List, Optional, Tuple

from termcolor import colored


class SharedReporting:
    """Shared functionality that various extended reporters might want to use."""

    FORMAT_STRING_STANDARD_COLUMN_LAYOUT = "{:<30} {:<10} {:<10} {:<10}"

    @staticmethod
    def colorized_threshold_string(
        trend_name: str,
        threshold: Dict[str, Any],
        format_string: str = FORMAT_STRING_STANDARD_COLUMN_LAYOUT,
    ) -> Tuple[str, bool]:
        """Build a colorized string for a threshold (based on success)."""
        formatted, any_errors_occurred = SharedReporting.plain_threshold_string(
            trend_name, threshold, format_string
        )
        success = SharedReporting.get_threshold_status(threshold)
        if success and not any_errors_occurred:
            colored_string = colored(formatted, "green", attrs=["bold"])
        else:
            colored_string = colored(formatted, "red", attrs=["bold"])

        return colored_string, any_errors_occurred

    @staticmethod
    def get_threshold_status(threshold: Dict[str, Any]) -> bool:
        """Perform a smart calculation of success for a single threshold."""
        try:
            success = threshold.get("succeeded") or False
        except (AttributeError, KeyError):
            success = False

        return success

    @staticmethod
    def plain_threshold_string(
        trend_name: str,
        threshold: Dict[str, Any],
        format_string: str = FORMAT_STRING_STANDARD_COLUMN_LAYOUT,
    ) -> Tuple[str, bool]:
        """Generate a human friendly string for a threshold."""
        any_errors_occurred = False
        try:
            formatted = format_string.format(
                trend_name,
                int(threshold["percentile"] * 100),
                f'{threshold["less_than_in_ms"]}ms',
                f'{int(threshold["actual_value_in_ms"])}ms',
            )
        except Exception as e:
            # catch any kind of error (structural) and replace with a meaningful error
            # line to get reported out to the destination
            formatted = (
                f"UNABLE TO PROCESS THRESHOLD FOR TREND <{trend_name}>: "
                f"{type(e).__name__} | {e}"
            )
            any_errors_occurred = True
        return formatted, any_errors_occurred

    @staticmethod
    def calculate_threshold_lines(
        trends: Dict[str, Dict[str, Any]],
        format_string: str = FORMAT_STRING_STANDARD_COLUMN_LAYOUT,
        formatter: Callable[
            [str, dict, Optional[str]], str
        ] = plain_threshold_string.__func__,
    ) -> List[str]:
        """Generate a list lines, one line per threshold.

        Parameters
        ----------
            trends (dict): dictionary of trends, typically from the locust stats object
            the key is the trendname, the value is thresh object

        Optional Parameters
        -------------------
            format_string: string, possibly containing placeholders for runtime values
            from the threshold object; the methods in this class pass the following
            values to the `.format(...)` method
                trend_name: str,
                percentile: int,
                less_than_in_ms: float,
                actual_value_in_ms: float
            formatter(Callable): method that will be used to format a single line for a
            single threshold; the parameters that this method must accept are
                trend_name: str,
                threshold: dict,
                optional format_string: str (see above for description of this format
                string)
            by default, it will use the method `plain_threshold_string` but you can
            also see another example in `colorized_threshold_string` on this class

        Returns
        -------
            list of lines (List[str]): List of lines calculated from the thresholds
        """
        lines = []

        try:
            # filter the trends down to only those that have at least one threshold
            # listed
            filtered_trends = {k: v for (k, v) in trends.items() if "thresholds" in v}

            # for each trend, get a string for each threshold & add to the list
            for trend_name, trend_values in filtered_trends.items():
                for threshold in trend_values["thresholds"]:
                    formatted, _ = formatter(trend_name, threshold, format_string)
                    lines.append(formatted)
        except AttributeError:
            # ignore error and just return an empty list
            pass

        return lines
