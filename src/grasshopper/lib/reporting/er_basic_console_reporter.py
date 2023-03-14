"""Module: ER Basic Console Reporter.

Can be used by any grasshopper tests by having a fixture that registers this reporter.
Serves as an example implementation of the IExtendedReporter interface.

"""
import logging
from typing import Any, Dict

from locust import env as locust_environment

from grasshopper.lib.reporting.iextendedreporter import IExtendedReporter
from grasshopper.lib.reporting.shared_reporting import SharedReporting

logger = logging.getLogger()
logger.propagate = True


class ERBasicConsoleReporter(IExtendedReporter):
    """Handle writing basic information to the console for a test run."""

    LINE = "-" * 80
    _name = "ER Basic Console Reporter"

    @classmethod
    def get_name(cls) -> str:
        """Retrieve the name for this er."""
        return cls._name

    @classmethod
    def set_name(cls, new_name: str) -> None:
        """Set the name for this er."""
        cls._name = new_name

    @classmethod
    def event_pre_suite(
        cls,
        suite_name: str,
        start_epoch: float,
        suite_args: Dict[str, Any] = {},
        **kwargs,
    ) -> None:
        """Report the grasshopper (pre)suite information to the console."""
        logger.info(cls.LINE)
        logger.info(
            f"Starting Suite {suite_name} at {start_epoch} with the following "
            f"arguments:"
        )
        for k, v in suite_args.items():
            logger.info(f"{k}=={v}")

    @classmethod
    def event_post_suite(
        cls,
        suite_name: str,
        start_epoch: float,
        end_epoch: float,
        suite_args: Dict[str, Any] = {},
        **kwargs,
    ) -> None:
        """Report the grasshopper (post)suite information to the console."""
        logger.info(f"Suite {suite_name} complete")
        logger.info(cls.LINE)

    @classmethod
    def event_pre_test(
        cls,
        test_name: str,
        start_epoch: float,
        test_args: Dict[str, Any] = {},
        **kwargs,
    ) -> None:
        """Report the grasshopper (pre)test information to the console."""
        logger.info(cls.LINE)
        logger.info(
            f"Starting Test {test_name} at {start_epoch} with the following arguments:"
        )
        for k, v in test_args.items():
            logger.info(f"{k}=={v}")

    @classmethod
    def event_post_test(
        cls,
        test_name: str,
        start_epoch: float,
        end_epoch: float,
        locust_environment: locust_environment = None,
        test_args: Dict[str, Any] = {},
        **kwargs,
    ) -> None:
        """Report the grasshopper (post)test information to the console."""
        logger.info(cls.LINE)
        logger.info(
            f"Test {test_name} complete at {end_epoch} with the following results:"
        )
        logger.info(f"Epoch time stamp: {start_epoch} - {end_epoch}")
        cls._report_thresholds_to_console(locust_environment.stats.trends)
        logger.info(cls.LINE)

    @staticmethod
    def _report_thresholds_to_console(trends: Dict[str, Dict[str, Any]]) -> None:
        """Print all the thresholds to the console in a pretty table."""
        logger.info("----------------------THRESHOLD REPORT-------------------------")
        logger.info(
            SharedReporting.FORMAT_STRING_STANDARD_COLUMN_LAYOUT.format(
                "Trend_Name", "Percentile", "Limit", "Actual"
            )
        )

        lines = SharedReporting.calculate_threshold_lines(
            trends, formatter=SharedReporting.colorized_threshold_string
        )
        for line in lines:
            logger.info(line)

        logger.info("--------------------END THRESHOLD REPORT-----------------------")
