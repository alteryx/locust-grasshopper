"""Module: Grasshopper.

The Grasshopper class is the main entry point for accessing
grasshopper functionality.

"""
import logging
import os
import signal
from typing import Dict, List, Optional, Type, Union

import gevent
import locust
from locust import LoadTestShape
from locust.env import Environment

from grasshopper.lib.journeys.base_journey import BaseJourney
from grasshopper.lib.util.listeners import GrasshopperListeners

logger = logging.getLogger()


class Grasshopper:
    """Main entry point to access addins and extensions."""

    def __init__(self, global_configuration: dict = {}, **kwargs):
        self.global_configuration = global_configuration
        self.log()

    def log(self) -> None:
        """Log all the configuration values."""
        logger.info("--- Grasshopper configuration ---")

        for k, v in self.global_configuration.items():
            logger.info(f"{k}: [{v}]")

        logger.info("--- /Grasshopper configuration ---")

    @property
    def influx_configuration(self) -> dict[str, Optional[str]]:
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

        return configuration

    @staticmethod
    def launch_test(
        weighted_user_classes: Union[
            Type[BaseJourney], List[Type[BaseJourney]], Dict[Type[BaseJourney], float]
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
        kwargs[
            "user_classes"
        ] = weighted_user_classes  # pass on the user classes as well

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
        env.runner.start_shape()
        gevent.spawn_later(
            kwargs.get("runtime"), lambda: os.kill(os.getpid(), signal.SIGINT)
        )
        env.runner.greenlet.join()

        return env

    @staticmethod
    def _assign_weights_to_user_classes(weighted_user_classes):
        for user_class, weight in weighted_user_classes.items():
            user_class.weight = weight

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
