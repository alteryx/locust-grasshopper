"""Module: BaseJourney.

Class to hold all the common functionality that we added on top of Locust's HttpUser
class.
"""
import signal
from uuid import uuid4

import gevent
from locust import HttpUser

import grasshopper.lib.util.listeners  # noqa: F401


class BaseJourney(HttpUser):
    """The base journey class for all other journey classes."""

    VUS_DICT = {}
    host = ""
    _incoming_test_parameters = {}
    abstract = True
    base_torn_down = False
    defaults = {"tags": {}, "thresholds": {}}

    @classmethod
    @property
    def incoming_scenario_args(cls):
        return cls._incoming_test_parameters

    @property
    def scenario_args(self):
        return self._test_parameters

    @classmethod
    def replace_incoming_scenario_args(cls, brand_new_args={}):
        """Replace the existing set of scenario_args with a new collection."""
        cls._incoming_test_parameters = brand_new_args

    @classmethod
    def update_incoming_scenario_args(cls, higher_precedence_args):
        """Add more values to scenario_args with higher precedence."""
        cls._incoming_test_parameters.update(higher_precedence_args)

    @classmethod
    def merge_incoming_scenario_args(cls, lower_precedence_args):
        """Add more values to scenario_args with lower precedence."""
        new_args = lower_precedence_args.copy()
        new_args.update(cls._incoming_test_parameters)
        cls.replace_incoming_scenario_args(new_args)

    @classmethod
    def reset_class_attributes(cls):
        """Reset the class level attributes to their starting state.

        We are using class level attributes because most of the time we want the state
        to be shared across all the instances of the class, since these values *should*
        always be the same across the instances and performance should be better without
        storing a copy for every instance.

        But in order to support unit testing and possibly other scenarios, this method
        is provided as a way to reset to the starting state.
        """
        cls._incoming_test_parameters = {}
        cls.defaults = {"tags": {}}
        cls.host = ""
        cls.abstract = True
        cls.base_torn_down = False
        BaseJourney.VUS_DICT = {}

    @classmethod
    def get_journey_object_given_vu_number(cls, vu_number):
        """Get the journey class if exists in the instance-level context, else None."""
        return cls.VUS_DICT.get(vu_number)

    def on_start(self):
        """Initialize the journey, set tags, and then set the test parameters."""
        super().on_start()
        self._merge_incoming_defaults_and_params()
        self._test_parameters = self._incoming_test_parameters.copy()
        self._set_base_teardown_listeners()
        self.client_id = str(uuid4())
        self._register_new_vu()
        self._set_thresholds()
        self.environment.host = self.scenario_args.get("target_url", "") or self.host

        # TODO: currently global iterations is stored in the environment stats object
        # TODO: poke around to see if we can move it to a class attribute here
        self.vu_iteration = 0

    def _register_new_vu(self):
        """Increment the user count and return the new vu's number."""
        self.vu_number = len(BaseJourney.VUS_DICT) + 1
        BaseJourney.VUS_DICT[self.vu_number] = self

    def _set_base_teardown_listeners(self):
        gevent.signal_handler(signal.SIGINT, self.teardown)  # ctrl-c teardown bind

    def _merge_incoming_defaults_and_params(self):
        self.merge_incoming_scenario_args(self.defaults)

    def _set_thresholds(self):
        self.environment.stats.trends = {}

        # If parameters are not passed in that need to be set, set them to the defaults
        for key, value in self.scenario_args.items():
            self._check_for_threshold_parameters_and_set_thresholds(
                parameter_key=key,
                parameter_value=value,
            )

    def _check_for_threshold_parameters_and_set_thresholds(
        self, parameter_key, parameter_value
    ):
        if parameter_key == "thresholds":
            for raw_trend_name, threshold_less_than_in_ms in parameter_value.items():
                trend_name, request_type = self._extract_trend_name(raw_trend_name)
                thresh_object = {
                    "less_than_in_ms": threshold_less_than_in_ms,
                    "actual_value_in_ms": None,
                    "percentile": 0.8,
                    "succeeded": None,
                    "http_method": request_type,
                }
                if trend_name in self.environment.stats.trends:
                    self.environment.stats.trends[trend_name]["thresholds"].append(
                        thresh_object
                    )
                else:
                    self.environment.stats.trends[trend_name] = {
                        "tags": self.scenario_args.get("tags", {}),
                        "thresholds": [thresh_object],
                    }

    @staticmethod
    def _extract_trend_name(raw_trend_name: str):
        if "{" in raw_trend_name and "}" in raw_trend_name:
            trend_name = raw_trend_name.split("}")[1]
            request_type = raw_trend_name.split("}")[0].split("{")[1].upper()
            return trend_name, request_type
        else:
            raise ValueError(
                "Invalid Trend Name! Please include the request type in curly "
                + "brackets. E.G: `{POST}post_job_group`, "
                + "`{CUSTOM}PX_TREND_photon_flow_run`, etc.."
            )

    def teardown(self, *args, **kwargs):
        """
        Tear down the journey and quit.

        The proper way to do your own tear down when extending this class is like so:
            def teardown(self, *args, **kwargs):
                # do your teardown stuff here
                super().teardown(*args, **kwargs)
        """
        self.base_torn_down = True
        stopped_vus = [vu.base_torn_down for vu in BaseJourney.VUS_DICT.values()]
        for i in range(60):
            if not all(stopped_vus):
                gevent.sleep(1)
            else:
                break
        BaseJourney.VUS_DICT = {}
        self.environment.runner.quit()
