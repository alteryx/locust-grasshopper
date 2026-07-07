"""Module: Grasshopper.

The Grasshopper class is the main entry point for accessing
grasshopper functionality.
"""

import logging
import os
import signal
from typing import Dict, List, Optional, Type, Union

if os.name == "posix":
    import resource  # pylint: disable=import-error

from functools import wraps

import gevent
import locust
from grasshopper.lib.journeys.base_journey import BaseJourney
from grasshopper.lib.util.listeners import GrasshopperListeners
from locust import LoadTestShape
from locust.env import Environment
from locust.exception import StopUser
from locust.user.task import DefaultTaskSet, TaskSet

logger = logging.getLogger()

# Store original TaskSet methods to restore after each test
_original_taskset_execute_task = TaskSet.execute_task
_original_default_taskset_execute_task = DefaultTaskSet.execute_task
_original_taskset_wait = TaskSet.wait


class Grasshopper:
    """Main entry point to access addins and extensions."""

    SENSITIVE_CONFIGURATION_KEYS = {
        "access_token",
        "datadog_api_key",
        "influx_pwd",
        "password",
        "rp_token",
        "rp_uuid",
        "workspace_token",
    }

    def __init__(self, global_configuration: dict = {}, **kwargs):
        self.global_configuration = global_configuration
        self.log()

    def log(self) -> None:
        """Log all the configuration values."""
        logger.info("--- Grasshopper configuration ---")
        for k, v in self.global_configuration.items():
            v = self._sanitize_configuration_value(k, v)
            logger.info(f"{k}: [{v}]")
        logger.info("--- /Grasshopper configuration ---")

    @classmethod
    def _sanitize_configuration_value(cls, key: str, value):
        """Redact sensitive values before logging."""
        if key == "target_url":
            return BaseJourney.normalize_url(value)
        if key in cls.SENSITIVE_CONFIGURATION_KEYS and value:
            return "***REDACTED***"
        return value

    @property
    def influx_configuration(self) -> dict[str, Optional[Union[bool, str]]]:
        """Extract the influx related configuration items.

        The InfluxDbSettings object should only get keys if there is a
        value coming from the command line. We _could_ define
        defaults here as well, but this somewhat breaks the
        principle of separation of concern.

        # TODO-DEPRECATED: move this code to the GHConfiguration object
        """
        configuration = {}

        host = self.global_configuration.get(
            "influx_host", self.global_configuration.get("influx_host")
        )
        if host:
            configuration["influx_host"] = host
        port = self.global_configuration.get("influx_port")
        if port:
            configuration["influx_port"] = port
        user = self.global_configuration.get("influx_user")
        if user:
            configuration["user"] = user
        pwd = self.global_configuration.get("influx_pwd")
        if pwd:
            configuration["pwd"] = pwd

        configuration["ssl"] = self.global_configuration.get("influx_ssl", False)
        configuration["verify_ssl"] = self.global_configuration.get(
            "influx_verify_ssl", False
        )

        return configuration

    @property
    def grafana_configuration(self) -> dict[str, Optional[str]]:
        """Extract the grafana related configuration items.

        # TODO-DEPRECATED: move this code to the GHConfiguration object
        """
        configuration = {}

        host = self.global_configuration.get(
            "grafana_host", self.global_configuration.get("influx_host")
        )
        configuration["grafana_host"] = host
        return configuration

    @property
    def datadog_configuration(self) -> dict[str, Optional[Union[dict, int, str]]]:
        """Extract the Datadog related configuration items."""
        configuration = {}

        api_key = self.global_configuration.get("datadog_api_key") or os.getenv(
            "DD_API_KEY"
        )
        if api_key:
            configuration["api_key"] = api_key

        site = self.global_configuration.get("datadog_site") or os.getenv("DD_SITE")
        configuration["site"] = site or "datadoghq.com"

        namespace = self.global_configuration.get("datadog_namespace") or "grasshopper"
        configuration["namespace"] = namespace

        default_tags = {}
        datadog_env = self.global_configuration.get("datadog_env") or os.getenv(
            "DD_ENV"
        )
        if datadog_env:
            default_tags["env"] = datadog_env

        datadog_service = self.global_configuration.get("datadog_service") or os.getenv(
            "DD_SERVICE"
        )
        if datadog_service:
            default_tags["service"] = datadog_service

        datadog_tags = self.global_configuration.get("datadog_tags") or os.getenv(
            "DD_TAGS"
        )
        if datadog_tags:
            default_tags.update(self._parse_datadog_tags(datadog_tags))

        if default_tags:
            configuration["default_tags"] = default_tags

        return configuration

    @staticmethod
    def _parse_datadog_tags(raw_tags: str) -> dict[str, str]:
        """Parse Datadog tag strings like `team:shield,test:navigation`."""
        parsed_tags = {}
        for raw_tag in str(raw_tags).split(","):
            raw_tag = raw_tag.strip()
            if not raw_tag:
                continue

            if ":" in raw_tag:
                key, value = raw_tag.split(":", 1)
            else:
                key, value = raw_tag, "true"

            parsed_tags[key.strip()] = value.strip()

        return parsed_tags

    @staticmethod
    def launch_test(
        weighted_user_classes: Union[
            Type[BaseJourney],
            List[Type[BaseJourney]],
            Dict[Type[BaseJourney], float],
        ],
        **kwargs,
    ) -> Environment:
        """
        Parametrize launching of locust test.

        Required parameters:
        - weighted_user_classes: this represents the answer to the question "what test
        should I launch?"

        The situation with user classes and weights is actually fairly complicated.
        In this context, the weight relates to how likely Locust is to pick that journey
        for the next virtual user it will spawn. Once that virtual user is going with
        journey, it will follow that journey's definition until the test terminates.

        In the simple case of a single journey or a composite sequential journey, this
        isn't that meaningful. In both cases, there is only one journey sent to Locust
        and weights are interesting if there is only one choice.

        You can supply:
        1. a single user class (journey) - in this case weights, for journey selection
        are ignored because Locust is only choosing from a set of 1
        2. a list of user_classes - in this case, weights are supplied so that all
        journeys have an equal chance of being selected
        3. a dictionary where the user classes are keys and the values are the weights
        - in this case, the weights come into play in selecting a journey

        It is important to note that once a user journey is selected for a particular
        vu, the definition of the journey (user class) comes into play. That journey
        also may use the @task decorator or the tasks attribute with a TaskSet to
        determine which __task__ is executed __each iteration__. An iteration is one
        time through the taskloop where Locust picks a task, executes it and waits the
        specified amount of time before starting the next iteration. The Shield team's
        journeys to date have only defined a single task per user class, but this will
        likely change as we build more complex journeys.

        Optional parameters:
            please see the documentation in grasshopper/pytest/commandline.py for a
            complete list of supported parameters

        TODO: this code is in need of a bit of refactor to pull out a few different
        TODO: steps - the normalizing of the incoming user classes into one standard
        TODO: format, processing the shape, setting up the Locust env & launching the
        TODO: the test - primarily, it's getting a little long and complex but also
        TODO: to have better separation of concerns
        """
        Grasshopper.set_ulimit()
        if isinstance(weighted_user_classes, type):  # if it's a class
            weighted_user_classes = {weighted_user_classes: 1}
        elif isinstance(weighted_user_classes, list):
            weighted_user_classes = {
                user_class: 1 for user_class in weighted_user_classes
            }

        # Actually, Locust always takes a __list__ of user classes and additional
        # information is set on each user class in this list to specify weight or
        # fixed count. That portion, setting weights, is handled after we process any
        # shape information below.
        user_classes = list(weighted_user_classes.keys())

        logger.debug(f"Launch received kwargs: {kwargs}")

        env = Environment(user_classes=user_classes)
        kwargs["user_classes"] = (
            weighted_user_classes  # pass on the user classes as well
        )

        env.grasshopper = Grasshopper(global_configuration=kwargs)
        env.create_local_runner()
        env.runner.stats.reset_all()
        gevent.spawn(locust.stats.stats_history, env.runner)
        env.grasshopper_listeners = GrasshopperListeners(environment=env)

        # env.shape_class is actually supplied a shape *instance*
        # despite the attr name
        env.shape_class = kwargs.get("shape_instance")
        kwargs["runtime"] = env.shape_class.configured_runtime

        # assign the weights to the individual user classes __after__ the shape has been
        # processed because eventually, we will need to consult the shape to get the max
        # number of virtual users
        Grasshopper._assign_weights_to_user_classes(weighted_user_classes)

        # Set up iteration limit if specified
        # Runtime-based termination is always set as a safeguard to prevent tests being stuck/run indefinitely
        iterations = kwargs.get("iterations", 0)
        runtime = kwargs.get("runtime")

        # Log test limits at the start
        if iterations > 0:
            logger.info(
                f"Test run limits: {runtime} seconds runtime and {iterations} iterations.\n"
                "Test will stop when either limit is reached first."
            )
            Grasshopper._setup_iteration_limit(env, iterations)
        else:
            logger.info(
                f"Test run limit: {runtime} seconds runtime.\n"
                "Test will stop when runtime is exhausted."
            )

        env.runner.start_shape()

        # Use a flag to track whether this specific test has already been stopped.
        # This prevents stale greenlets from previous tests from interfering with
        # the current test, and ensures the stop message is only logged once.
        test_stopped = [False]

        def handle_runtime_limit():
            if test_stopped[0]:
                return
            test_stopped[0] = True
            # Check if iteration limit was already reached
            if not (
                hasattr(env.runner, "iterations_exhausted")
                and env.runner.iterations_exhausted
            ):
                # Runtime limit reached first
                logger.info(
                    f"Test stopped: Runtime limit of {runtime} seconds reached."
                )
            os.kill(os.getpid(), signal.SIGINT)

        runtime_greenlet = gevent.spawn_later(runtime, handle_runtime_limit)

        try:
            env.runner.greenlet.join()
        finally:
            # Cancel the runtime timer greenlet if it hasn't fired yet.
            # This is critical when running multiple scenarios sequentially in the
            # same process (e.g., YAML scenario files): without cancellation, stale
            # runtime timers from earlier tests can fire during later tests, causing
            # premature termination, incorrect "Runtime limit reached" messages, or
            # silent test interruption.
            test_stopped[0] = True
            runtime_greenlet.kill(block=False)

        return env

    @staticmethod
    def _assign_weights_to_user_classes(weighted_user_classes):
        for user_class, weight in weighted_user_classes.items():
            user_class.weight = weight

    @staticmethod
    def _reset_iteration_limit():
        """Reset TaskSet methods to their original state.

        This must be called before setting up a new iteration limit to ensure
        the previous test's state doesn't affect the new test.
        """
        TaskSet.execute_task = _original_taskset_execute_task
        DefaultTaskSet.execute_task = _original_default_taskset_execute_task
        TaskSet.wait = _original_taskset_wait

    @staticmethod
    def _setup_iteration_limit(env: Environment, iterations: int):
        """Set up iteration limiting for the test.

        This method patches TaskSet.execute_task to track iterations and stop
        the test when the iteration limit is reached.
        Args:
            env: The Locust Environment object
            iterations: Maximum number of iterations to run
        """
        # First, restore original methods to clear any previous test's state
        Grasshopper._reset_iteration_limit()

        runner = env.runner
        runner.iterations_count = 0
        runner.iterations_exhausted = False

        def iteration_limit_wrapper(method):
            @wraps(method)
            def wrapped(self, task):
                if runner.iterations_count >= iterations:
                    if not runner.iterations_exhausted:
                        runner.iterations_exhausted = True
                        logger.info(
                            f"Test stopped: Iteration limit of {iterations} reached."
                        )
                        # Trigger stop
                        os.kill(os.getpid(), signal.SIGINT)
                    raise StopUser()
                try:
                    method(self, task)
                finally:
                    runner.iterations_count = runner.iterations_count + 1

            return wrapped

        # Patch TaskSet methods to add iteration limiting
        # We patch the original methods, not the potentially already-patched ones
        TaskSet.execute_task = iteration_limit_wrapper(_original_taskset_execute_task)
        DefaultTaskSet.execute_task = iteration_limit_wrapper(
            _original_default_taskset_execute_task
        )

        # Patch TaskSet.wait to skip sleep if iteration limit has been reached
        def wrapped_wait(self):
            if runner.iterations_count >= iterations:
                return
            _original_taskset_wait(self)

        TaskSet.wait = wrapped_wait

    @staticmethod
    def load_shape(shape_name: str, **kwargs) -> LoadTestShape:
        """Return the instantiated shape instance given string shape name."""
        shape_name = shape_name.capitalize()  # to make sure it is capitalized
        import grasshopper.lib.util.shapes as shapes

        if shape_name in dir(shapes):
            return getattr(shapes, shape_name)(**kwargs)
        else:
            raise ValueError(
                f"Shape {shape_name} does not exist in "
                f"grasshopper.lib.util.shapes! Please check the spelling."
            )

    @staticmethod
    def set_ulimit():
        """Increase the maximum number of open files allowed."""
        # Adapted from locust source code, main function in locust.main.
        try:
            if os.name == "posix":
                minimum_open_file_limit = 10000
                current_open_file_limit = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
                if current_open_file_limit < minimum_open_file_limit:
                    # Increasing the limit to 10000 within a running process
                    # should work on at least MacOS. It does not work on all OS:es,
                    # but we should be no worse off for trying.
                    resource.setrlimit(
                        resource.RLIMIT_NOFILE,
                        [minimum_open_file_limit, resource.RLIM_INFINITY],
                    )
        except BaseException:
            logger.warning(
                f"""System open file limit '{current_open_file_limit}' is below minimum
                setting '{minimum_open_file_limit}'. It's not high enough for load
                testing, and the OS didn't allow locust to increase it by itself. See
                https://github.com/locustio/locust/wiki/Installation#increasing-maximum-number-of-open-files-limit
                for more info."""
            )
