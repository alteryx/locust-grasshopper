"""Module: ReporterExtensions."""
# Standard Library
import logging
from typing import Any, Dict, List

from grasshopper.lib.reporting.iextendedreporter import IExtendedReporter

logger = logging.getLogger()


class ReporterExtensions:
    """Class to hold the registration information for extended reporters (listeners).

    Across this entire class, using `er` = extended reporter for space reasons
    """

    EVENTS = [
        "event_pre_test",
        "event_post_test",
        "event_pre_suite",
        "event_post_suite",
    ]
    _ers: dict[str, IExtendedReporter] = []

    @classmethod
    def register_er(cls, er: IExtendedReporter) -> None:
        """Register an instance of an er."""
        try:
            cls._ers[er.get_name()] = er
        except Exception as e:
            # intentionally catching all exceptions so that if there is a problem with
            # an extended reporter it won't a) get registered & b) affect anything else
            logger.warning(
                f"Error in [register_er] with reporter extension: {type(e).__name__} | "
                f"{e}"
            )

    @classmethod
    def unregister_er(cls, er_name: str) -> None:
        """Unregister an instance, by key, of an er."""
        try:
            del cls._ers[er_name]
        except KeyError as e:
            # ignore and log warning if asked to unregister something that isn't
            # currently registered
            logger.warning(e)

    @classmethod
    @property
    def registrations(cls) -> Dict[str, IExtendedReporter]:
        """Return the list of currently registered ers."""
        return cls._ers

    @classmethod
    @property
    def ers(cls) -> List[IExtendedReporter]:
        return [v for k, v in cls._ers.items()]

    @classmethod
    def clear_registrations(cls) -> None:
        """Clear all registrations, mainly used to support unit testing."""
        cls._ers = {}

    @classmethod
    def _notify_event(cls, event: str, *args, **kwargs) -> None:
        for er in cls.ers:
            try:
                logger.debug(
                    f"Calling event {event} on reporter extension {er.get_name()}"
                )
                event_method = getattr(er, event)
                event_method(*args, **kwargs)
            except Exception as e:
                # intentionally catching ALL exceptions so that a faulty extension will
                # not ever affect other reporters or the main test process
                logger.warning(
                    f"Error in event [{event}] on reporter extension [{er.get_name()}]:"
                    f" {type(e).__name__} | {e}"
                )

    @classmethod
    def notify_pre_test(
        cls,
        test_name: str,
        start_epoch: float,
        test_args: Dict[str, Any] = {},
        **kwargs,
    ):
        """Call the pre-test event on all registered ers."""
        cls._notify_event(
            "event_pre_test", test_name, start_epoch, test_args=test_args, **kwargs
        )

    @classmethod
    def notify_pre_suite(cls, suite_name, start_epoch, suite_args={}, **kwargs):
        """Call the pre-suite event on all registered ers."""
        cls._notify_event(
            "event_pre_suite", suite_name, start_epoch, suite_args=suite_args, **kwargs
        )

    @classmethod
    def notify_post_suite(
        cls, suite_name, start_epoch, end_epoch, suite_args={}, **kwargs
    ):
        """Call the post-suite event on all registered ers."""
        cls._notify_event(
            "event_post_suite",
            suite_name,
            start_epoch,
            end_epoch,
            suite_args=suite_args,
            **kwargs,
        )

    @classmethod
    def notify_post_test(
        cls,
        test_name,
        start_epoch,
        end_epoch,
        locust_env,
        test_args={},
        **kwargs,
    ):
        """Call the post-test event on all registered ers."""
        cls._notify_event(
            "event_post_test",
            test_name,
            start_epoch,
            end_epoch,
            locust_env,
            test_args=test_args,
            **kwargs,
        )
