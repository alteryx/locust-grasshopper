"""Module: IExtendedReporter."""

from abc import ABC, abstractmethod

from locust import env as locust_environment


class IExtendedReporter(ABC):
    """Abstract class that defines the interface that all er classes must implement."""

    @classmethod
    @abstractmethod
    def get_name(cls) -> str:
        """Get the name of this extended reporter."""

    @classmethod
    @abstractmethod
    def set_name(cls, new_name) -> str:
        """Set the name for this extended reporter."""

    @abstractmethod
    def event_pre_suite(
        self, suite_name: str, start_epoch: float, suite_args: dict = {}, **kwargs
    ):
        """Call by ReporterExtensions when a pre-suite event occurs."""

    @abstractmethod
    def event_post_suite(
        self,
        suite_name: str,
        start_epoch: float,
        end_epoch: float,
        suite_args: dict = {},
        **kwargs
    ):
        """Call by ReporterExtensions when a post-test event occurs."""

    @abstractmethod
    def event_pre_test(
        self, test_name: str, start_epoch: float, test_args: dict = {}, **kwargs
    ):
        """Call by ReporterExtensions when a pre-test event occurs."""

    @abstractmethod
    def event_post_test(
        self,
        test_name: str,
        start_epoch: float,
        end_epoch: float,
        locust_env: locust_environment = None,
        test_args: dict = {},
        **kwargs
    ):
        """Call by ReporterExtensions when a post-test event occurs."""
