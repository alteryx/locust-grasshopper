"""Locust Custom Shapes.

Sometimes, a completely custom shaped load test is required that cannot be achieved by
simply setting or changing the user count and spawn rate. For example, one might want to
generate a load spike or ramp up and down at custom times. By using a one of these
classes which extend LoadTestShape, we have full control over the user count and spawn
rate at all times.
"""
import json
import logging

from locust import LoadTestShape

logger = logging.getLogger()


class Default(LoadTestShape):
    """Base shape for our all Load test shapes.

    Replicate passing only runtime, spawn rate, users on the command line.
    Also serves as the Base for the rest of our shapes, so that the launch method knows
    how to instantiate. Note that all shapes now take in additional args in the
    constructor, they are not obligated to do anything with them.
    """

    DEFAULT_RUNTIME = 120

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.users = kwargs.get("users") or 1
        self.spawn_rate = kwargs.get("spawn_rate") or 1
        self.runtime = kwargs.get("runtime") or self.DEFAULT_RUNTIME
        self._configured_runtime = self.runtime

    @property
    def configured_runtime(self):
        return self._configured_runtime

    def get_shape_overrides(self):
        """Return a dict of values that this shape would like to override.

        A shape definition takes precedence over the and may provide new values for
        runtime, spawn_rate and users. Since this is the base implementation, we don't
        have an overrides to provide.

        """
        return {}

    def tick(self):
        """Tell locust about the new values for users and spawn rate.

        Called by locust about 1x/second, allowing the shape to adjust the values over
        time or terminate the test.

        Per the locust documentation, return None to terminate the test. When using
        locust as a library, you must also set a different greenlet to send the quit
        message when runtime has elapsed to (see the launch method).
        """
        return self.users, self.spawn_rate


class Smoke(Default):
    """Shape to run for smoke tests, use set values."""

    def __init__(self, *args, **kwargs):
        super().__init__(runtime=60, users=1, spawn_rate=1)

    def get_shape_overrides(self):
        """Return overrides from this shape.

        Smoke is a shape that has hardcoded values, so we want to override whatever the
        user might passed for the shape related values. Shape name always takes
        precedence over the runtime, spawn_rate and users values.

        """
        return {"runtime": 60, "users": 1, "spawn_rate": 1}


class Testingfixturesonly(Default):
    """Shape for testing fixtures, DO NOT USE!!."""

    testing_values = {
        "runtime": 10,
        "users": 20,
        "spawn_rate": 0.004,
        "key_that_should_not_override": "some value",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(**self.testing_values)

    def get_shape_overrides(self):
        """Return overrides from this shape.

        Smoke is a shape that has hardcoded values, so we want to override whatever the
        user might have passed for the shape related values. Shape always takes
        precedence over the runtime, spawn_rate and users values.

        """
        return self.testing_values


class Trend(Default):
    """Convenience shape with our standard trend parameters."""

    # for the trend shape, override the default to 10m
    DEFAULT_RUNTIME = 600
    USERS = 10
    SPAWN_RATE = 0.1

    def __init__(self, *args, **kwargs):
        kwargs["users"] = self.USERS
        kwargs["spawn_rate"] = self.SPAWN_RATE
        # don't specify runtime here because mostly we want it
        # to pick up the runtime from scenario yaml
        super().__init__(*args, **kwargs)

    def get_shape_overrides(self):
        """Return a dict of values that this shape would like to override."""
        return {"users": self.USERS, "spawn_rate": self.SPAWN_RATE}


class Stages(Default):  # noqa E501
    """
    Stolen and slightly modified from this set of examples as part of the locust.io
    documentation.
    https://github.com/locustio/locust/blob/master/examples/custom_shape/stages.py

    Keyword arguments:
        stages -- A list of dicts, each representing a stage with the following keys:
            duration -- When this many seconds pass the test is advanced to the next
            stage.
            users -- Total user count
            spawn_rate -- Number of users to start/stop per second

    Most likely, you'd want to extend this class and only define a new stages attr.
    """

    stages = [
        {"duration": 60, "users": 1, "spawn_rate": 1},
        {"duration": 60, "users": 2, "spawn_rate": 2},
        {"duration": 60, "users": 3, "spawn_rate": 3},
        {"duration": 60, "users": 4, "spawn_rate": 4},
        {"duration": 60, "users": 3, "spawn_rate": 1},
        {"duration": 60, "users": 1, "spawn_rate": 1},
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._configured_runtime = self.sum_duration(self.stages)

    def tick(self):
        """Tell locust about the new values for users and spawn rate."""
        run_time = self.get_run_time()
        previous_stages_runtimes = 0
        for stage in self.stages:
            if run_time < stage["duration"] + previous_stages_runtimes:
                tick_data = (stage["users"], stage["spawn_rate"])
                return tick_data
            previous_stages_runtimes += stage["duration"]

        return None

    @staticmethod
    def sum_duration(stages):
        """Sum and return all stage durations."""
        return sum(int(stage["duration"]) for stage in stages)


class Spike(Stages):
    """A spike shape that adds many users quickly, then cools down after.

    Takes the following parameters from the command line
    users = target number of users for spike stage
    spawn_rate = how quickly to add the users during the spike stage
    runtime = how long to make the *spike* stage, not that the cooldown stage gets
    added on so the total length of the shape is runtime + cooldown_duration
    cooldown_duration = how much time to take to get back to 1 user (uses same spawn
    rate as the spike for now); if omitted, will use the runtime

    """

    stages = [{"duration": 10, "users": 1, "spawn_rate": 1}]  # effectively a no-op

    def __init__(self, *args, **kwargs):
        users = kwargs.get("users") or 1
        spike_duration = kwargs.get("runtime") or 600
        spawn_rate = kwargs.get("spawn_rate") or users / spike_duration
        # checking kwargs still allows someone to create another shape that extends the
        # this spike shape but with a different cooldown. if you use this shape
        # directly, you will always get a 10m cooldown period
        cooldown_duration = kwargs.get("cooldown_duration") or 600
        cooldown_spawn_rate = users / cooldown_duration
        self.stages = [
            {"duration": spike_duration, "users": users, "spawn_rate": spawn_rate},
            {
                "duration": spike_duration + cooldown_duration,
                "users": 1,
                "spawn_rate": cooldown_spawn_rate,
            },
        ]
        super().__init__(*args, **kwargs)


class Customstages(Stages):  # noqa E501

    """Keyword arguments:
    stages -- can be either a json string or a dictionary object

    This can be set by overriding the complete configuration before launching the
    test, or, setting the following grasshopper_scenario_args in your YAML scenario
    like so:


    grasshopper_args:
        shape: customstages
    grasshopper_scenario_args:
        stages:
          - duration: 10
            users: 1
            spawn_rate: 4
          - duration: 20
            users: 2
            spawn_rate: 2

    """

    stages = [
        {"duration": 68, "users": 4, "spawn_rate": 0.5},
        {"duration": 62, "users": 2, "spawn_rate": 1},
        {"duration": 72, "users": 6, "spawn_rate": 0.5},
        {"duration": 66, "users": 3, "spawn_rate": 1},
        {"duration": 76, "users": 8, "spawn_rate": 0.5},
        {"duration": 64, "users": 4, "spawn_rate": 1},
        {"duration": 12, "users": 0, "spawn_rate": 1},
    ]

    def __init__(self, *args, **kwargs):
        try:
            stages = kwargs.get("stages")
            if type(stages) == str:
                stages = json.loads(stages)
            self.stages = stages
        except TypeError:
            pass
        super().__init__(*args, **kwargs)
