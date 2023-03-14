"""Module: Grasshopper.

The Grasshopper class is the main entry point for accessing
grasshopper functionality.

"""
import logging
import os
import signal
from typing import Optional, Type, Union

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

        """
        configuration = {}
        # use legacy influxdb host arg if supplied
        host = self.global_configuration.get(
            "influx_host", self.global_configuration.get("influxdb")
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
        user_classes: Union[Type[list[BaseJourney]], Type[BaseJourney]],
        **kwargs,
    ) -> Environment:
        """
        Parametrize launching of locust test.

        Required parameters:
        - user_classes: The journey classes that the runner will run. This can
        be a list or just a singular class.


        Optional parameters:
            please see the documentation in grasshopper/pytest/commandline.py for a
            complete list of supported parameters

        """
        if type(user_classes) != list:
            user_classes = [user_classes]

        logger.debug(f"Launch received kwargs: {kwargs}")

        env = Environment(user_classes=user_classes)
        kwargs["user_classes"] = user_classes  # pass on the user classes as well

        env.grasshopper = Grasshopper(global_configuration=kwargs)
        env.create_local_runner()
        env.runner.stats.reset_all()
        gevent.spawn(locust.stats.stats_history, env.runner)
        env.grasshopper_listeners = GrasshopperListeners(environment=env)

        # always running with a shape, if none is supplied then use Default shape which
        # behaves the same as if you supplied a target users, spawn_rate and run_time
        # this shape will use 1 user, 1 user/second, runtime of 120s if no values are
        # supplied

        # env.shape_class is actually supplied a shape *instance*
        # despite the attr name
        if "shape_instance" in kwargs.keys():
            env.shape_class = kwargs.get("shape_instance")
        elif "shape" in kwargs.keys():
            env.shape_class = Grasshopper.load_shape(kwargs.get("shape"), **kwargs)
        else:
            env.shape_class = Grasshopper.load_shape("Default", **kwargs)

        logger.debug(f"Selected shape class is {env.shape_class}")

        # fetch runtime from the shape, might be different than the
        # value in kwargs
        # TODO: should we actually get the shape override the values
        # TODO: from px_args?
        runtime = env.shape_class.configured_runtime
        env.runner.start_shape()
        gevent.spawn_later(runtime, lambda: os.kill(os.getpid(), signal.SIGINT))
        env.runner.greenlet.join()

        return env

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
